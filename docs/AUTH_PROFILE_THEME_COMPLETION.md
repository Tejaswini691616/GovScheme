# Authentication, Profile and Theme Completion

Implemented from the SmartGov AI master prompt, while leaving DigiLocker unchanged/deferred.

## Authentication
- Registration validation includes password confirmation and minimum length.
- Login/logout are implemented and security events are audit logged.
- Forgot-password requests use secure random OTPs, hashed in session, 10-minute expiry, five-attempt limit, single-use verification, and a generic response for unknown emails.
- Reset requests are rate-limited in the session.
- Local DEBUG mode has a clearly labelled developer-console OTP fallback when SMTP is not configured; the OTP is not shown in the normal web UI.
- Passwords are stored with Werkzeug password hashing.
- Change password requires the current password and confirmation.
- Change email preserves user_id and checks duplicate/normalized email.
- Change phone requires the current password and validates the phone format.
- Security events are written without passwords, hashes, OTPs, API keys, or secrets.

## Profile
- Edit Profile covers personal information, citizen information, eligibility flags, document/readiness-related profile fields, and demographic information already represented by the database.
- Account Security is visible on the profile page with Change Password, Change Email, and Change Phone forms.
- Language, theme, text size and reduced-motion preferences are shown and linked to Settings.

## Themes and accessibility
- Light
- Dark
- System (uses OS preference)
- Indian Civic
- High Contrast
- Large text
- Reduced motion
- High-contrast form controls
- Existing language selector remains available globally.

## Verification
- Python compileall passed for the modified source tree.
- Full runtime import/test execution requires the project's Python dependencies to be installed in the execution environment; the build environment used for this package does not contain Flask, so runtime pytest could not be executed there.

## Deferred by user request
- Live DigiLocker integration remains deferred.
