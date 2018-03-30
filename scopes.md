# Scopes expected by pushsnapscript

* `project:releng:snapcraft:firefox:{candidate,beta,mock}`: This represents the Snap store channel pushsnap script publishes the snap to. pushsnapscript only accepts a subset of what the [Snap store allows](https://docs.snapcraft.io/reference/channels#risk-levels-meaning).
  * `mock` is a specific custom value. Using it will prevent pushsnapscript from contacting the Snap store.


## Firefox (nightly, beta, release) vs Snap store (edge, beta, candidate, release)?
 Snap store allows a product to have 4 different channels (`edge`, `beta`, `candidate`, `release`). Tracks are used by end-users when they want to enroll in a less stable version of Firefox.

| Product    | Brand name                | Track                      | Notes           |
| ---------- | ------------------------- | -------------------------- | --------------- |
| release    | Firefox                   | `candidate` then `release` |                 |
| beta       | Firefox Beta              | `beta`                     |                 |
| devedition | Firefox Developer Edition | none                       | Not shipped yet |
| nightly    | Firefox Nightly           | none                       | Not shipped yet |
