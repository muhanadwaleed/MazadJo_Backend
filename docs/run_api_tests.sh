#!/usr/bin/env sh
set -e
cd "$(dirname "$0")/.."
exec .venv/bin/python manage.py test accounts.tests.test_api_integration accounts.tests.test_auth_phase1 accounts.tests.test_registration_otp catalog.tests.test_seed_catalog auctions.test_draft_list_api auctions.test_media_api auctions.test_lifecycle_api auctions.test_watchlist_api bidding.tests -v2
