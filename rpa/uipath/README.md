# UiPath integration

`Main.xaml` is the reviewed UiPath process boundary for the SmartGov AI prototype. It is **not claimed to be a tested live government robot** because UiPath Studio/Robot is not available in this build environment.

## Process boundary

- Receives structured application and citizen inputs.
- Opens the operator-supplied application portal.
- Enters only the configured repetitive fields.
- Does not bypass CAPTCHA, OTP, biometric checks, login controls, or other security controls.
- Portal failures are reported as `Needs Manual Action`.
- A successful application reference is returned only when the reviewed portal workflow actually supplies one.

## Portal-specific configuration

The selectors in `Main.xaml` are generic UiPath web selectors. Before a real deployment, the administrator must open the process in UiPath Studio, review the target portal's actual DOM/selectors, and test the process against a portal where automation is permitted. SmartGov AI does not claim that these selectors work against an arbitrary government website.

Document submission is intentionally not fabricated. If a reviewed application portal requires document upload, configure a permitted document source and exact portal selector in the UiPath process, or stop for manual action. Do not download/re-upload DigiLocker documents unnecessarily when the official application portal supports DigiLocker retrieval.

## Orchestrator

Configure `RPA_MODE=UIPATH` and the Orchestrator tenant/client/release settings only after the process has been reviewed and published. The Flask application starts and polls the configured Orchestrator job and never falls back to a fake successful submission when the live path fails.

Until a real UiPath environment is configured and tested, keep `RPA_MODE=DEMO`. Demo references are prefixed `DEMO-` and are explicitly identified as prototype references.
