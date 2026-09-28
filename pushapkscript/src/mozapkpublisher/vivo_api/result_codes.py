"""
The response codes the vivo publishing API returns.

vivo reports failures at two independent levels, and the outer one saying "success" does
not mean the call worked:

  - `code` is the *gateway* result. A non-zero value means the request never reached the
    publishing service -- a bad signature is code "23" -- and such a response carries no
    `subCode` at all.
  - `subCode` is the *business* result. A failure here arrives as HTTP 200 with
    `"code": "0"`, `"msg": "success"` and even `"success": true`, with the real reason in
    `subCode`/`subMsg`. Trusting `success` alone therefore reads a refused publication as
    a completed one, which is why `raise_for_response_code` checks both.

Only the codes the client branches on live here; `raise_for_response_code` surfaces any
other code verbatim.

See "vivo Developers Open API Service Documentation", section "List of Interfaces in the
Publishing API", at https://developer.vivo.com/
"""

# Both `code` and `subCode` use "0" for success.
SUCCESS_CODE = "0"

# `subCode` values meaning the app is in a state that forbids any update. These are not
# transient in any sense we can wait out: each one needs a human to finish or abandon
# something in the vivo Developers console, so they are reported rather than retried.
# The mapped text completes the sentence "vivo refused the update because ...".
APP_STATE_FORBIDS_UPDATE = {
    "A0305": "the app is already under review",
    "A0306": "the app is pending publication",
    "A0307": "the app is being tested",
    "B0302": "the app is already being updated",
}
