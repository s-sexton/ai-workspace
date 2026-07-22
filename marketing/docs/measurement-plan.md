# SendThisFile Marketing Measurement Plan

## Purpose

This document will define how SendThisFile tracks marketing-site performance
during and after the move from WordPress to static HTML5 pages served through
Cloudflare.

## Goals

- Preserve trustworthy traffic and conversion measurement during migration.
- Remove stale or duplicate tags.
- Define clear funnel events for GA4.
- Support low-cost A/B tests and landing-page experiments.
- Keep measurement implementation reviewable and testable.

## Current Inventory To Collect

- Google Tag Manager container export.
- Current GA4 property and data stream details.
- Current key events and conversions.
- Current tags, triggers, variables, and custom HTML snippets.
- Third-party pixels and scripts.
- Current WordPress plugins that inject scripts or tracking.
- Existing forms, signup links, pricing links, downloads, and outbound links.
- Existing consent or privacy behavior.

## Event Model Draft

Use GA4 recommended events where they fit, and use custom events only when
recommended events do not describe the business action clearly.

Initial candidate events:

- `page_view`
- `view_pricing`
- `select_plan`
- `sign_up`
- `generate_lead`
- `contact_submit`
- `file_download`
- `outbound_click`
- `login_click`
- `support_click`

## Funnel Draft

Initial funnel views:

- Organic landing page to pricing.
- Organic landing page to signup.
- Comparison or use-case page to signup.
- Homepage to pricing to signup.
- Contact page view to lead submission.
- Campaign landing page to lead or signup.

## Architecture Questions

- Should critical GA4 events remain in client-side GTM for launch?
- Which non-critical scripts, if any, should move to Cloudflare Zaraz?
- How will static pages publish `dataLayer` events consistently?
- How will redirects preserve UTMs and attribution?
- How will A/B test variants be routed and reported?
- What consent behavior is required before any analytics event fires?

## Launch QA Checklist Draft

- GTM Preview confirms expected tags fire.
- GA4 DebugView receives expected events and parameters.
- Pageviews are not duplicated.
- Conversion events fire once.
- UTMs survive redirects and form/signup paths.
- Internal traffic filters are understood.
- Old WordPress-only scripts are removed.
- Canonical URLs are correct.
- Redirects preserve SEO value.
- Top landing pages have measurable next actions.
