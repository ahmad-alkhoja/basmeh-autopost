#!/usr/bin/env python3
"""Basmeh auto-poster.

Each run publishes the next post in posts.json to Instagram (and the Facebook
page, if enabled), then records it in state.json so it is never posted twice.

Environment:
  PAGE_TOKEN        Facebook Page access token (GitHub secret)
  POST_TO_FACEBOOK  "true" to also post on the Facebook page (default true)
  MODE              "post" (default) | "check"  (check = test setup, posts nothing)
  POST_ID           optional: post this id from posts.json instead of the next one
"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error

GRAPH = os.environ.get("GRAPH_BASE", "https://graph.facebook.com") + "/" + \
    os.environ.get("GRAPH_VERSION", "v23.0")
HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("PAGE_TOKEN", "").strip()
MODE = os.environ.get("MODE", "post").strip() or "post"
POST_TO_FB = os.environ.get("POST_TO_FACEBOOK", "true").strip().lower() == "true"
FORCE_ID = os.environ.get("POST_ID", "").strip()
REPO = os.environ.get("GITHUB_REPOSITORY", "")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
IMAGE_BASE = os.environ.get(
    "IMAGE_BASE", f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/images/")


class ApiError(Exception):
    pass


def api(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{GRAPH}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise ApiError(f"{method} {path} -> HTTP {e.code}: {body}") from None


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(os.path.join(HERE, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def accounts():
    """Find the Page and its linked Instagram account from the Page token."""
    page = api("GET", "me", fields="id,name,instagram_business_account{id,username}")
    ig = page.get("instagram_business_account")
    if not ig:
        raise ApiError("The Facebook page has no linked Instagram business account, "
                       "or the token is missing instagram_basic permission.")
    return page, ig


def image_url(name):
    return IMAGE_BASE + urllib.parse.quote(name)


def wait_ready(container_id):
    for _ in range(30):
        st = api("GET", container_id, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise ApiError(f"Instagram could not process media {container_id}: {st}")
        time.sleep(5)
    raise ApiError(f"Instagram media {container_id} not ready after 150s")


def post_instagram(ig_id, post):
    imgs = post["images"]
    if len(imgs) == 1:
        c = api("POST", f"{ig_id}/media", image_url=image_url(imgs[0]),
                caption=post["caption"])["id"]
    else:
        kids = []
        for name in imgs:
            kid = api("POST", f"{ig_id}/media", image_url=image_url(name),
                      is_carousel_item="true")["id"]
            wait_ready(kid)
            kids.append(kid)
        c = api("POST", f"{ig_id}/media", media_type="CAROUSEL",
                children=",".join(kids), caption=post["caption"])["id"]
    wait_ready(c)
    return api("POST", f"{ig_id}/media_publish", creation_id=c)["id"]


def post_facebook(page_id, post):
    imgs = post["images"]
    if len(imgs) == 1:
        r = api("POST", f"{page_id}/photos", url=image_url(imgs[0]),
                message=post["caption"])
        return r.get("post_id") or r["id"]
    params = {"message": post["caption"]}
    for i, name in enumerate(imgs):
        pid = api("POST", f"{page_id}/photos", url=image_url(name),
                  published="false")["id"]
        params[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    return api("POST", f"{page_id}/feed", **params)["id"]


def check(posts):
    page, ig = accounts()
    print(f"OK  Facebook page : {page['name']} ({page['id']})")
    print(f"OK  Instagram     : @{ig.get('username')} ({ig['id']})")
    missing = []
    for p in posts["queue"] + posts["extra"]:
        for name in p["images"]:
            if not os.path.exists(os.path.join(HERE, "images", name)):
                missing.append(name)
    if missing:
        print(f"MISSING {len(missing)} image(s) in images/: {', '.join(missing[:10])}")
        return 1
    # make sure GitHub serves the images publicly (Instagram downloads them from there)
    first = posts["queue"][0]["images"][0]
    try:
        with urllib.request.urlopen(urllib.request.Request(image_url(first), method="HEAD"), timeout=30) as r:
            print(f"OK  Images public : {image_url(first)} ({r.headers.get('Content-Type')})")
    except Exception as e:  # noqa: BLE001
        print(f"FAIL Image not reachable at {image_url(first)}: {e}  (is the repo public?)")
        return 1
    state = load("state.json")
    nxt = state["next"]
    print(f"OK  Next post     : {posts['queue'][nxt]['id'] if nxt < len(posts['queue']) else 'none - queue finished'}")
    print("Setup looks good. Nothing was posted.")
    return 0


def main():
    if not TOKEN:
        print("PAGE_TOKEN secret is missing. See SETUP.md step 3.")
        return 1
    posts = load("posts.json")
    if MODE == "check":
        return check(posts)

    state = load("state.json")
    if FORCE_ID:
        found = [p for p in posts["queue"] + posts["extra"] if p["id"] == FORCE_ID]
        if not found:
            print(f"No post with id {FORCE_ID}")
            return 1
        post, advance = found[0], False
    else:
        if state["next"] >= len(posts["queue"]):
            print("All posts in the queue are published. Add more to posts.json.")
            return 0
        post, advance = posts["queue"][state["next"]], True

    page, ig = accounts()
    print(f"Posting {post['id']} ({len(post['images'])} image(s)) to @{ig.get('username')}")
    entry = {"id": post["id"], "time": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}
    entry["instagram"] = post_instagram(ig["id"], post)
    print(f"Instagram OK: {entry['instagram']}")
    # Instagram is the main channel: once it's live, never re-post this item.
    if advance:
        state["next"] += 1
    state["history"].append(entry)
    save_state(state)

    fb_error = None
    if POST_TO_FB:
        try:
            entry["facebook"] = post_facebook(page["id"], post)
            print(f"Facebook OK: {entry['facebook']}")
        except ApiError as e:
            fb_error = str(e)
            entry["facebook_error"] = fb_error
        save_state(state)
    if fb_error:
        print(f"Facebook FAILED (Instagram was posted): {fb_error}")
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ApiError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
