# Rolling back a deploy

Currently, there are two ways to roll back a scriptworker pool deploy:

- [force] push the previous-known-good revision to the `production-____script` branch and wait for its `k8s-image` task to finish, or
- find the `k8s-image` task that deployed the previous-known-good image to docker hub, and either `rerun (force)` it (if its deadline hasn't passed) or `retrigger` it.

(In the future, Aki would love to see release promotion graphs that can push previously built k8s-image docker images to the right kubernetes clusters, but we've long wanted this and have yet to be able to prioritize it.)

## How to find the previous revision

Because git and Github don't have a pushlog, it's difficult to tell what the previous revision to a given branch is: the green checks, red X's, and yellow dots could be checks from a PR or push to another branch. If weeks or months pass between pushes to a given branch, you might have to check many many revisions before you find the previous revision in the branch. And because we support both the `production` and `production-____script` branches to deploy scriptworkers, we need to check to see which branch had the newer previous-most-recent push.

Enter docker hub. We push our scriptworker docker images to the [mozilla org](https://hub.docker.com/u/mozilla). You can find the repositories at `https://hub.docker.com/r/mozilla/releng-____script/`, e.g. [`https://hub.docker.com/r/mozilla/releng-signingscript/`](https://hub.docker.com/r/mozilla/releng-signingscript/) for signingscript.

We tag each push with multiple tags. You can view the tags by recency, e.g. [`https://hub.docker.com/r/mozilla/releng-signingscript/tags?page=1&ordering=last_updated`](https://hub.docker.com/r/mozilla/releng-signingscript/tags?page=1&ordering=last_updated).

The `production` and `dev` tags are set to the most recent push. But the other tags are of interest here: they're named `production-DATESTRING-REVISION` or `dev-DATESTRING-REVISION`. For instance, the signingscript `production-20210929025643-7995c5bb123bbfc25e3d7f81c46f3d7ba49cbe89` tag was pushed on 2021-09-29 at 02:56:43 (UTC?), from revision `7995c5bb123bbfc25e3d7f81c46f3d7ba49cbe89`.

If the most recent `production-DATESTRING-REVISION` tag is known busted, and the previous `production-DATESTRING-REVISION` tag is days or weeks old, most likely that previous tag was known good for that period of time. Take the revision in that tag, and force-push it to the `production-____script` branch.
