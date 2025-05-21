#!/usr/bin/env python3

import argparse
import asyncio

from mozapkpublisher.sgs_api.auth import create_jwt_for_auth, create_access_token


async def main(args: argparse.Namespace) -> None:
    with open(args.key_path) as fd:
        jwt = create_jwt_for_auth(args.service_account_id, ["publishing"], fd.read())

    print(await create_access_token(jwt))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("service_account_id")
    parser.add_argument("key_path")

    args = parser.parse_args()
    asyncio.run(main(args))
