# Khobornama Telegram Auto Publisher

Hourly GitHub Actions workflow that polls the Khobornama API and posts unseen news items to a public Telegram channel with the featured image, title, summary and article link.

## Important: confirm your API schema first

The supplied API base URL is `https://api.khobornama.info.bd/api/`. This project defaults to `NEWS_ENDPOINT=news/` and supports common list response shapes:
- a JSON array
- `{ "results": [...] }` (Django REST Framework)
- `{ "data": [...] }`, `{ "news": [...] }`, or `{ "articles": [...] }`

It recognizes common fields:
- ID: `id`, `pk`, `news_id`, `article_id`
- title: `title`, `headline`, `name`
- description: `short_description`, `summary`, `excerpt`, `description`, `content`
- featured image: `featured_image`, `image`, `thumbnail`, `cover_image`, `banner`
- URL: `url`, `absolute_url`, `link`, or `slug`

If your API uses different names, edit `NEWS_ENDPOINT` or `article_fields()` in `main.py`. Do not assume the endpoint or field names are correct until you inspect the API response.

## 1. Create the Telegram bot

1. Talk to https://t.me/BotFather and create a bot using `/newbot`.
2. Add the bot to your public Telegram channel as an administrator.
3. Give it permission to post messages.
4. Use the public channel username in `TELEGRAM_CHAT_ID`, e.g. `@khobornama`.

Keep the bot token private. Never commit it to this repository.

## 2. Create a public GitHub repository

Create a repository, e.g. `khobornama-telegram-automation`, and upload these files.

## 3. Configure repository secrets

Repository -> Settings -> Secrets and variables -> Actions -> New repository secret:

- `TELEGRAM_BOT_TOKEN`: token from BotFather
- `TELEGRAM_CHAT_ID`: public channel username, e.g. `@khobornamabd`
- `FACEBOOK_PAGE_ID`: numeric Facebook Page ID (e.g. `123456789012345`)
- `FACEBOOK_PAGE_ACCESS_TOKEN`: permanent Page Access Token with `pages_manage_posts`
- `API_BASE_URL`: `https://api.khobornama.info.bd/api/` (optional, defaults automatically)

Under Variables (or Secrets), add:

- `NEWS_ENDPOINT`: actual news-list endpoint relative to API base, e.g. `news/`
- `SITE_BASE_URL`: `https://khobornama.info.bd`

The `news/` endpoint is only a default example. Check your actual API routes before the first run.

## 4. Enable workflow permissions

Repository -> Settings -> Actions -> General -> Workflow permissions:
- Select **Read and write permissions**
- Save

This is needed because the workflow commits `data/posted_ids.json` after successful posts.

## 5. Test

1. Open Actions -> Khobornama Telegram Auto Publisher.
2. Select Run workflow.
3. Open the run logs and verify the API response is parsed.
4. Confirm the test post appears in the Telegram channel.

The first run posts all items returned by the endpoint (up to `MAX_NEWS_PER_RUN`). For a safe first test, temporarily set `DRY_RUN=true` as a workflow environment variable in the YAML, run once, then remove it before real publishing.

## 6. Schedule

The cron `0 * * * *` runs at the start of every hour in UTC. GitHub Actions cron is UTC, so this is also every hour in Bangladesh. GitHub may delay scheduled workflows during high load; it is not a guaranteed exact-time scheduler.

## 7. Customization

- Change `MAX_NEWS_PER_RUN` in the workflow if needed.
- Change `NEWS_ENDPOINT` repository variable to the correct list endpoint.
- If the API requires authentication, add a repository secret and add the appropriate Authorization header in `get_json()`.
- If API pagination uses a format other than `next`, adapt `find_list()` / `fetch_news()`.

## Operational notes

- `data/posted_ids.json` is committed back to the public repository. It contains article IDs only; do not store personal data or tokens in it.
- The project uses GitHub Actions `contents: write` permission to persist deduplication state.
- If an execution fails after Telegram accepts a message but before GitHub saves the state, the same item may be sent again on the next run. For stronger exactly-once behavior, use a small external database or a Telegram-posted marker stored by the source API.
- GitHub scheduled workflows can be delayed and may be disabled for inactive public repositories. Check the Actions tab periodically.
- Telegram photo captions have a 1,024-character limit. The script shortens descriptions to fit.
