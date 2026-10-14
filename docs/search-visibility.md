# Search visibility rollout

The homepage and three static guides explain the builder in crawlable HTML.
They have distinct titles and descriptions, internal links, and official sources.
The homepage includes WebApplication structured data describing actual features.

## Production setup

1. Canonical links and sitemap entries default to the verified production
   origin, `https://www.njitschedulepro.com`. Set `NEXT_PUBLIC_SITE_URL` before
   building only if the public domain changes. Preview deployments also point
   their canonicals to production.
2. Deploy the frontend and verify `/robots.txt`, `/sitemap.xml`, and the three
   `/guides/` URLs. Ensure hosting protection does not block public crawlers.
3. Verify the domain in Google Search Console and Bing Webmaster Tools. Submit
   `/sitemap.xml` and inspect the homepage and guide URLs for indexing.
4. Seek genuine links from NJIT clubs, student resource lists, and relevant
   campus publications. Share a demo in communities where promotion is allowed.
5. Track target query impressions, clicks, and successful schedule generations
   from search. Recheck after indexing and during registration season.

Run `python3 scripts/check_search_visibility.py` after deployment to verify
HTTP status, canonical links, indexability, structured data, crawler rules,
and sitemap entries against the public production site.

The homepage publishes the Google Search Console verification tag for the
production URL-prefix property. Keep it in place to maintain verification.

After deploying new or updated public content, run
`python3 scripts/submit_indexnow.py` to notify participating search engines of
the current sitemap URLs. It first checks the deployed ownership file and
rejects URLs outside the production origin. An accepted notification does not
guarantee indexing. Do not submit unchanged URLs repeatedly.

`robots.txt` allows public crawlers, including search crawlers used by AI tools,
and excludes the API path. It is not an access-control mechanism. Private shared
schedule query URLs are not included in the sitemap; the homepage canonical
points to the clean root URL.

The initial guide targets are NJIT schedule building, scheduling around work,
and calendar export. Expand only when there is a distinct student need and
enough useful information to answer it. Rankings are not guaranteed by these
changes.
