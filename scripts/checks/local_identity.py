"""Check signed employee claims from local Keycloak without submitting them to AWS."""
import base64
import http.cookiejar
import json
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree


class Form(HTMLParser):
    def __init__(self):
        super().__init__()
        self.action = None
        self.fields = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "form":
            self.action = attributes.get("action")
        if tag == "input" and attributes.get("name"):
            self.fields[attributes["name"]] = attributes.get("value", "")


class LocalRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlparse(newurl).hostname != "localhost":
            raise ValueError("Smoke check refuses to follow a redirect outside localhost")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class LocalCookiePolicy(http.cookiejar.DefaultCookiePolicy):
    def return_ok_secure(self, cookie, request):
        # Browsers treat localhost as a secure context; stdlib CookieJar does not.
        if urllib.parse.urlparse(request.full_url).hostname == "localhost":
            return True
        return super().return_ok_secure(cookie, request)


def employee_assertion(username, password):
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar(LocalCookiePolicy())),
        LocalRedirect(),
    )
    url = "http://localhost:8081/realms/mybank/protocol/saml/clients/aws"
    with opener.open(url, timeout=10) as response:
        login = Form()
        login.feed(response.read().decode())
    if not login.action or urllib.parse.urlparse(login.action).hostname != "localhost":
        raise ValueError("Expected a local Keycloak login form")
    login.fields.update(username=username, password=password)
    request = urllib.request.Request(
        login.action, data=urllib.parse.urlencode(login.fields).encode(),
    )
    with opener.open(request, timeout=10) as response:
        result = Form()
        result.feed(response.read().decode())
    if result.action != "https://signin.aws.amazon.com/saml":
        path = urllib.parse.urlparse(result.action or "").path
        raise ValueError(f"Expected AWS form; received path {path}, fields {sorted(result.fields)}")
    return ElementTree.fromstring(base64.b64decode(result.fields["SAMLResponse"]))


def main():
    realm = json.loads(Path("identity/generated/mybank-realm.json").read_text())
    groups = {group["name"]: group["attributes"]["aws_roles"] for group in realm["groups"]}
    ns = {"s": "urn:oasis:names:tc:SAML:2.0:assertion"}
    for user in realm["users"]:
        assertion = employee_assertion(user["username"], user["credentials"][0]["value"])
        role_attribute = assertion.find(
            ".//s:Attribute[@Name='https://aws.amazon.com/SAML/Attributes/Role']", ns,
        )
        assert role_attribute is not None
        actual = [value.text for value in role_attribute.findall("s:AttributeValue", ns)]
        assert actual == groups[user["groups"][0].lstrip("/")]
        signature = assertion.find(
            ".//s:Assertion/{http://www.w3.org/2000/09/xmldsig#}Signature", ns,
        )
        assert signature is not None
        assert assertion.find(".//s:Audience", ns).text == "urn:amazon:webservices"
    print("PASS: both employees receive separate role claims in signed local SAML assertions")


if __name__ == "__main__":
    main()
