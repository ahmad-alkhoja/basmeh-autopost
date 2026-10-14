# Basmeh auto-poster

Posts the next Basmeh post to Instagram + Facebook every **Sunday, Tuesday and Thursday at ~8:00 PM (Amman)**.
Runs free on GitHub Actions. You only touch it if GitHub emails you that a run failed.

| File | What it is |
|---|---|
| `posts.json` | All posts in order (images + caption). `queue` = posted one by one, `extra` = occasion posts you trigger by hand |
| `state.json` | Progress. `next` = index of the next post (0 = first). Updated automatically after each post |
| `images/` | The post images (JPG, 1080×1350) |
| `post.py` | The script that posts |
| `.github/workflows/post.yml` | The schedule |

---

## One-time setup (about 20 minutes)

### 1. Instagram must be a Business account linked to the Facebook page
Instagram app → Settings → **Account type and tools** → make sure it's **Business** (Professional).
Then in Instagram → Settings → **Accounts Center**, make sure the Basmeh Instagram and the Basmeh Facebook page are connected.

### 2. Put this folder on GitHub (public repo)
1. On github.com click **New repository** → name `basmeh-autopost` → **Public** → Create.
   *(Public is needed so Instagram can download the images. Your token stays secret.)*
2. In Terminal on your Mac:
   ```bash
   cd ~/Desktop/"All Projects "/basmeh-autopost
   git init -b main && git add . && git commit -m "Basmeh auto-poster"
   git remote add origin https://github.com/ahmad-alkhoja/basmeh-autopost.git
   git push -u origin main
   ```

### 3. Get a Page token from Meta (it never expires)
1. Go to **developers.facebook.com/apps** → **Create app** → name it `Basmeh Poster`.
   When asked for a use case/type, pick **Other** → **Business** (the wording changes sometimes; any option that lets you add Facebook Login / Pages / Instagram permissions works).
2. Open **developers.facebook.com/tools/explorer** (Graph API Explorer):
   - **Meta App**: choose `Basmeh Poster`
   - **User or Page**: *Get User Access Token*
   - Add these permissions:
     `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `business_management`
   - Click **Generate Access Token** and allow access to the **Basmeh** page and Instagram account.
3. Copy the token → open **developers.facebook.com/tools/debug/accesstoken** → paste → **Debug** → at the bottom click **Extend Access Token** → copy the new long token.
4. Back in Graph API Explorer, paste that long token in the token box, type `me/accounts` in the query bar and click **Submit**.
   In the result, find the Basmeh page and copy its `access_token` value.
5. (Check) Paste it in the Access Token Debugger: it should say **Type: Page** and **Expires: Never**.

> Never paste this token in a chat or a file. It only goes into GitHub secrets (next step).

### 4. Give the token to GitHub
Your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
- Name: `PAGE_TOKEN`
- Secret: the page token from step 3

*(Optional)* To post on Instagram only: **Variables** tab → New variable `POST_TO_FACEBOOK` = `false`.

### 5. Test it
Repo → **Actions** tab → enable workflows if asked → **Basmeh auto-post** → **Run workflow** → mode **check** → Run.
Open the run: you should see `OK` lines for the page, Instagram, images and the next post. Nothing is posted in check mode.

**Done.** From now on it posts by itself on schedule.

---

## Everyday use (only if you want to)
- **Post the next one right now:** Actions → Run workflow → mode `post`.
- **Post the occasion greeting:** Actions → Run workflow → mode `post`, post_id `99_occasion_greeting_template`.
- **Skip ahead / go back:** edit `next` in `state.json` on GitHub (0 = first post in the queue).
- **Pause:** Actions → Basmeh auto-post → `...` → **Disable workflow**.
- **Change the days/time:** edit the `cron` line in `.github/workflows/post.yml` (times are UTC; Amman = UTC+3).
- **If a run fails** GitHub emails you. Open the run to see the error. The most common cause is the token stopped working (for example after changing your Facebook password): redo step 3 and update the secret.
- Boosting a post is still done by hand in the Instagram app (the API can't pay for ads).
