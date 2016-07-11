IMAGE_NAME = fbs

build:
	docker build -t $(IMAGE_NAME) --no-cache --rm .

start:
	docker run -it --rm --name $(IMAGE_NAME)-container $(IMAGE_NAME)

shell:
	docker exec -ti $(IMAGE_NAME)-container /bin/bash --login


update_pubkeys:
	curl https://hg.mozilla.org/mozilla-central/raw-file/default/toolkit/mozapps/update/updater/nightly_aurora_level3_primary.der | openssl x509 -inform DER -pubkey -noout > keys/nightly.pubkey
	curl https://hg.mozilla.org/mozilla-central/raw-file/default/toolkit/mozapps/update/updater/dep1.der | openssl x509 -inform DER -pubkey -noout > keys/dep.pubkey
	curl https://hg.mozilla.org/mozilla-central/raw-file/default/toolkit/mozapps/update/updater/release_primary.der | openssl x509 -inform DER -pubkey -noout > keys/release.pubkey
