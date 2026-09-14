"""
The `ret.code` values the AppGallery publishing API returns, and the sub-codes it embeds
in `ret.msg`.

Only the codes the client actually branches on live here. Mirroring the whole published
table would be a copy we cannot keep honest -- it is long, it changes, and a stale copy is
worse than none -- so `raise_for_ret_code` surfaces any unrecognised code verbatim
alongside the doc URL instead of translating it.

https://developer.huawei.com/consumer/en/doc/AppGallery-connect-References/agcapi-publishingapi-errorcode-0000001163523297
"""

# "The package is being compiled. Please try again 3 to 5 minutes later."
# Unambiguous: this code has exactly one meaning, so the code alone decides.
PACKAGE_COMPILING = 204144727

# "Failed to query the app information when the API for submitting an app for release is
# called."
#
# Overloaded, and the reason this module exists. Its documented meaning is a set of
# permanent AAB failures, listed below, which it reports by embedding a sub-code in the
# message. But AppGallery also returns this same code, with no sub-code, while it is still
# parsing a freshly uploaded package -- a transient state that has no result code of its
# own. So the code cannot decide on its own; see PERMANENT_SUBMIT_SUB_CODES and
# PACKAGE_PROCESSING_MESSAGES for how the two are told apart.
SUBMIT_QUERY_FAILED = 204144660

# The sub-codes SUBMIT_QUERY_FAILED embeds in its message. Every one is permanent, so a
# message carrying any of them is never retried regardless of its prose.
PERMANENT_SUBMIT_SUB_CODES = (
    "80210099",  # uses dynamic features but does not integrate the Dynamic Ability SDK
    "80210100",  # universal.apk cannot run properly due to invalid module configurations
    "80210101",  # Asset Pack is not supported
    "80210102",  # failed to download the AAB package
    "80210103",  # failed to download the AAB package: it is empty
    "80210104",  # failed to decompress the AAB package: invalid format
    "80210105",  # failed to parse the AAB package using the bundletool
    "80210106",  # failed to compile the AAB package
    "80210116",  # AAB package size exceeds the upper limit (150 MB)
)

# Message substrings that mark SUBMIT_QUERY_FAILED as "still parsing" rather than
# permanently failed. Matching prose is unpleasant, but the transient state has no result
# code and no sub-code of its own, so the message is the only signal there is. Each
# fragment is wording AppGallery has actually been observed to return:
#
#   "is being processed" / "it may take"
#       "[cds]submit failed, additional msg is [The pkg: [firefox.apk] is being
#        processed. It may take 2-5 minutes, depending on the size of the software
#        package.]"
#   "parsing"
#       the shorter English variant of the same state
#   "解析中"
#       literally "parsing in progress" -- the API answers in Chinese for some accounts,
#       and this is the wording Huawei's own console uses for the parsing state
#
# Deliberately absent: a bare "parse" or "解析". Sub-code 80210105 is the *permanent*
# "Failed to parse the AAB package using the bundletool", so matching the bare verb would
# retry a hard failure for the whole timeout window and then report a timeout instead of
# the real error. PERMANENT_SUBMIT_SUB_CODES guards that case too; the narrow fragments
# here are the second line of defence for a permanent message that carries no sub-code,
# such as "registeredEntity can not be empty".
PACKAGE_PROCESSING_MESSAGES = ("is being processed", "it may take", "parsing", "解析中")
