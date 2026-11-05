# Serene Bay — Business Profile poster (routine prompt)

Posts each newly live insight to Serene Bay's Google Business Profile. A post
there is public immediately, so this routine only posts what a human has
already merged into production (`beta` in serene-2) and is live on
serenebay.ae. It drafts nothing and merges nothing.

## One-time setup

1. **Google Cloud project** (approved for Business Profile API access). In
   APIs & Services → Library, enable at least:
   - Google My Business API (creates the posts)
   - My Business Account Management API
   - My Business Business Information API
2. **OAuth consent screen**: publishing status **In production**. In Testing,
   Google expires the refresh token after 7 days and posting stops.
3. **OAuth client**: Credentials → Create credentials → OAuth client ID →
   type **Desktop app**. Keep the client ID and secret.
4. **Sign in once**, on your own computer, as the profile's **owner**:

       pip install requests
       python3 gbp_auth.py --client-id <id> --client-secret <secret>

   It prints `GBP_REFRESH_TOKEN`, `GBP_ACCOUNT_ID` and `GBP_LOCATION_ID`.
5. **Routine environment** (the Serene environment can be reused):
   - API credentials: `GBP_CLIENT_ID`, `GBP_CLIENT_SECRET`,
     `GBP_REFRESH_TOKEN`, plus the existing `GITHUB_TOKEN` and
     `POWERAUTOMATE_WEBHOOK_URL`.
   - Variables: `GBP_ACCOUNT_ID`, `GBP_LOCATION_ID`, `GBP_POST_SINCE` (the
     day you switch it on, YYYY-MM-DD), `SERENE_LIVE_BRANCH=beta`,
     `SERENE_REPO_PATH`.
   - Network policy must allow `oauth2.googleapis.com`,
     `mybusiness.googleapis.com` and `www.serenebay.ae`.
   - Setup script: `setup.sh`, as for the weekly routine.
6. **Dry run first**: `python3 post_to_gbp.py --dry-run` shows exactly what
   would post, without posting.

Suggested trigger: daily, mid-morning Dubai time. One post per run at most, so
a backlog drains a day at a time rather than flooding the profile.

---

Post the next newly live Serene Bay insight to the Google Business Profile.
Never post anything that is not live on serenebay.ae.

1. Run `pip install -r requirements.txt`.
2. Run `python3 post_to_gbp.py`. It reads `GBP_POST_SINCE` from the
   environment, lists insights on the production branch of the serene-2 clone,
   checks each is live on serenebay.ae, skips any the profile already links
   to, and posts at most one. It sends the Teams message itself.
3. If it prints "nothing new to post", stop. That is the normal result on most
   days and needs no notification.
4. If it exits non-zero it has already posted `{"event":"run_failed"}` to the
   webhook. Do not retry the post by hand or call the API yourself: report the
   error it printed and stop. An `invalid_grant` error means the sign-in must
   be redone with `gbp_auth.py`.

Commit nothing: the profile's own post list is the record of what was posted.
