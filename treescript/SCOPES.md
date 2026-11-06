# Scopes
Treescript derives the actions to perform from the task's scopes, of the form
`project:{trust_domain}:{repo}:treescript:action:{action}`.

Supported actions:
* `version_bump`
  * Treescript will perform a version bump as specified in the tasks payload.
* `create_branch`
  * Treescript will create a branch as specified in the tasks payload.
