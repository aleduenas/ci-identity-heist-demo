# Mybank | Security Engineer, Purple Team (P1/P2) Case Study

## Overview

Mybank is a fintech platform helping small businesses manage money collaboratively. The Purple Team tests Mybank's defences, runs tabletop and phishing exercises, and builds the tooling and guardrails that turn findings into lasting fixes.

This case study is for intermediate candidates (P1/P2). We want to see how you reason about an attack, whether you can build something small that works, how you use AI tools in your work, and how you explain what you did to people outside security.

## Ground rules for candidates

- Do not test, scan, or interact with any real Mybank system, domain, or employee. Everything here is a simulation on paper or in your own sandbox.
- Do not use real customer or employee data. Invent names and data where you need them.
- You are expected to use AI tools (Claude, ChatGPT, Copilot, or similar). Tell us where you used them and what you checked by hand. We care about your judgement, not about whether the first draft was yours.
- Submit a short write-up (2 to 3 pages) plus whatever you built. A public GitHub repo, a Gist, or a zip is fine.
- If something in the scenario is unclear, make an assumption, write it down, and keep going. We will discuss it in the debrief.

## Operation Leaky Pipeline

### Scenario

Mybank runs on AWS with EKS for container orchestration. Engineers ship daily through a GitHub to CI/CD to EKS pipeline. Access is managed through SAML single sign-on, and a small number of employees hold elevated access to customer data for support and debugging. Engineers across the company are increasingly using AI coding assistants and agentic workflows, which means more people are writing and deploying code, and not all of them have a security background.

The Purple Team wants to know whether a developer laptop or a CI job being compromised would be caught, and how quickly. You have been asked to pick one realistic attack path through the developer environment, build a small control or detection for it, and show how you would prove it works.

### Objectives

1. Describe two realistic attack paths an attacker could use to reach customer or financial data through the developer environment (for example: a leaked GitHub Actions secret, an over-permissive IAM role, a malicious npm package, a stolen session token from a developer laptop).
2. Pick one of them and build a small, working control or detection. Examples: a script that audits GitHub Actions workflows for long-lived AWS keys; a SIEM detection rule (in pseudo-config is fine) for suspicious IAM role assumption; a pre-commit or CI check that blocks a known-bad pattern; a Kubernetes network policy with a test that proves it blocks the traffic it should.
3. Write a validation plan: how you would safely simulate the attack to confirm your control fires, and what you would measure.
4. Write a short summary an engineering team could act on.

## Deliverables

- **Presentation:**
  - The two attack paths, why you picked the one you built for, your assumed attacker profile, your validation plan, and what you would do next with more time.
  - The script, rule, policy, or check you built. Bonus points: you can demo your sample script against mock data during the presentation.
- **AI usage note:**
  - What you asked AI tools to do, what they got wrong or you did not trust, and what you verified yourself.
- **Engineer summary:**
  - A message you would post in an engineering channel explaining the risk, the fix, and what you need from them.

## Format

Please come prepared to walk us through your case study and findings. Expect questions from the interviewers along the way, and we'll leave time at the end for any questions you have for us. This interview will take approximately 1 hour.