"""AWS SAML relying-party contract and claims."""

AWS_SAML = "https://signin.aws.amazon.com/saml"
AWS_CLAIMS = "https://aws.amazon.com/SAML/Attributes/"


def mapper(name, provider, config):
    return {
        "name": name, "protocol": "saml", "protocolMapper": provider,
        "config": {"attribute.nameformat": "URI Reference", **config},
    }


def aws_client():
    return {
        "clientId": "urn:amazon:webservices", "name": "AWS Mybank Sandbox",
        "enabled": True, "protocol": "saml", "fullScopeAllowed": False,
        "frontchannelLogout": True, "redirectUris": [AWS_SAML],
        "defaultClientScopes": [], "optionalClientScopes": [],
        "attributes": {
            "saml.assertion.signature": "true", "saml.server.signature": "true",
            "saml.signature.algorithm": "RSA_SHA256",
            "saml.client.signature": "false", "saml.force.post.binding": "true",
            "saml.encrypt": "false", "saml.authnstatement": "true",
            "saml_name_id_format": "username", "saml_force_name_id_format": "true",
            "saml_assertion_consumer_url_post": AWS_SAML,
            "saml_idp_initiated_sso_url_name": "aws",
            "saml.server.signature.keyinfo.ext": "false",
        },
        "protocolMappers": [
            mapper("AWS group roles", "saml-user-attribute-mapper", {
                "user.attribute": "aws_roles", "attribute.name": AWS_CLAIMS + "Role",
                "aggregate.attrs": "true",
            }),
            mapper("AWS session name", "saml-user-property-mapper", {
                "user.attribute": "username", "attribute.name": AWS_CLAIMS + "RoleSessionName",
            }),
        ],
    }
