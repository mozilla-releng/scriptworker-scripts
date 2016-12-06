IMAGE_NAME = balrogworker

build: Dockerfile
	docker build -t $(IMAGE_NAME)  --rm .

start:
	docker run -it --rm --name $(IMAGE_NAME)-container $(IMAGE_NAME)

shell:
	docker exec -ti $(IMAGE_NAME)-container /bin/bash --login

Dockerfile:
	cp docker/Dockerfile Dockerfile


update_pubkeys:
	curl https://hg.mozilla.org/mozilla-central/raw-file/default/toolkit/mozapps/update/updater/nightly_aurora_level3_primary.der | openssl x509 -inform DER -pubkey -noout > balrogscript/keys/nightly.pubkey
	curl https://hg.mozilla.org/mozilla-central/raw-file/default/toolkit/mozapps/update/updater/dep1.der | openssl x509 -inform DER -pubkey -noout > balrogscript/keys/dep.pubkey
	curl https://hg.mozilla.org/mozilla-central/raw-file/default/toolkit/mozapps/update/updater/release_primary.der | openssl x509 -inform DER -pubkey -noout > balrogscript/keys/release.pubkey
