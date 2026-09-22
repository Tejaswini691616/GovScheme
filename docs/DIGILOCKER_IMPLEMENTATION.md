# DigiLocker Document Access and Readiness

The project now contains an authorized-integration boundary rather than a fake live DigiLocker client.

## Implemented

- Official DigiLocker portal handoff.
- Configurable OAuth authorization, token exchange and document-metadata endpoints.
- OAuth state validation in the user's server-side session.
- No DigiLocker password, PIN or OTP collection.
- No DigiLocker scraping.
- No access tokens stored in SQLite or audit logs.
- Minimum document availability metadata only.
- Scheme-specific document requirements stored only when source-derived and explicitly verified by an administrator.
- Readiness calculation from verified scheme requirements + authorized document metadata.
- Missing / available / verification-required states.
- Connection, unavailable and permission-required states.
- Local disconnect that removes stored DigiLocker metadata.
- Chatbot document-readiness intent using the same readiness service.
- Application detail page exposes the same readiness result.
- No profile field is treated as proof of document availability.

## Live configuration boundary

The project does not invent DigiLocker API endpoints. To enable live access, configure the endpoint/client values supplied by an authorized DigiLocker integration:

- `DIGILOCKER_ENABLED=1`
- `DIGILOCKER_CLIENT_ID`
- `DIGILOCKER_CLIENT_SECRET`
- `DIGILOCKER_AUTH_URL`
- `DIGILOCKER_TOKEN_URL`
- `DIGILOCKER_DOCUMENTS_URL`
- `DIGILOCKER_REDIRECT_URI`
- `DIGILOCKER_SCOPE`

If those values are absent, the UI clearly reports that live integration is unavailable and links to the official DigiLocker portal.
