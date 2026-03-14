"""
NarrativeForge — AI Visual Generation
Generate character portraits, scene illustrations, cover art.
Supports: DALL-E 3 (OpenAI key), Stable Diffusion (local Automatic1111),
          Replicate API, or any OpenAI-compatible image endpoint.
User supplies their own API key — NarrativeForge never stores it.
"""
import os
import re
import html as _html
import io
import requests
import streamlit as st


# ── Provider configs ────────────────────────────────────────────────────────
_PROVIDERS = {
    "DALL-E 3 (OpenAI)": {
        "key_label": "OpenAI API Key",
        "key_placeholder": "sk-...",
        "docs": "https://platform.openai.com/api-keys",
        "free": False,
    },
    "Stable Diffusion (local)": {
        "key_label": "SD Web UI URL",
        "key_placeholder": "http://127.0.0.1:7860",
        "docs": "https://github.com/AUTOMATIC1111/stable-diffusion-webui",
        "free": True,
    },
    "Replicate": {
        "key_label": "Replicate API Token",
        "key_placeholder": "r8_...",
        "docs": "https://replicate.com/account/api-tokens",
        "free": False,
    },
}

_STYLES = {
    "Photorealistic":         "photorealistic, highly detailed, 8k resolution, cinematic lighting",
    "Oil Painting":           "oil painting, classical art style, detailed brushwork, warm tones",
    "Watercolour":            "watercolour illustration, soft edges, flowing colours, artistic",
    "Fantasy Art":            "fantasy concept art, epic illustration, detailed, dramatic lighting",
    "Dark Gothic":            "dark gothic art, moody atmosphere, dramatic shadows, high contrast",
    "Anime / Manga":          "anime style, vibrant colours, clean lines, manga illustration",
    "Ink Sketch":             "ink sketch, detailed linework, black and white, crosshatching",
    "3D Render":              "3D render, octane render, studio lighting, photorealistic textures",
    "Vintage Book Cover":     "vintage book cover illustration, retro art style, bold composition",
    "Storybook Illustration": "storybook illustration, charming, whimsical, warm colours",
}


def _call_dalle(api_key: str, prompt: str, size="1024x1024") -> bytes | str:
    """Call DALL-E 3 API. Returns image bytes or error string."""
    try:
        r = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={"model": "dall-e-3", "prompt": prompt,
                  "n": 1, "size": size, "response_format": "url"},
            timeout=60)
        r.raise_for_status()
        url = r.json()["data"][0]["url"]
        img = requests.get(url, timeout=30)
        return img.content
    except requests.HTTPError as e:
        return f"API error: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"Error: {e}"


def _call_sd(base_url: str, prompt: str, negative="") -> bytes | str:
    """Call Stable Diffusion WebUI API (txt2img)."""
    try:
        r = requests.post(
            f"{base_url.rstrip('/')}/sdapi/v1/txt2img",
            json={"prompt": prompt, "negative_prompt": negative or "blurry, low quality, watermark",
                  "steps": 30, "cfg_scale": 7, "width": 512, "height": 768,
                  "sampler_name": "DPM++ 2M Karras"},
            timeout=120)
        r.raise_for_status()
        import base64
        b64 = r.json()["images"][0]
        return base64.b64decode(b64)
    except Exception as e:
        return f"SD Error: {e}"


def _call_replicate(api_token: str, prompt: str) -> bytes | str:
    """Call Replicate API with SDXL model."""
    try:
        # Start prediction
        r = requests.post(
            "https://api.replicate.com/v1/models/stability-ai/sdxl/predictions",
            headers={"Authorization": f"Token {api_token}",
                     "Content-Type": "application/json"},
            json={"input": {"prompt": prompt, "num_outputs": 1,
                            "width": 1024, "height": 1024}},
            timeout=30)
        r.raise_for_status()
        pred = r.json()
        pred_id = pred["id"]

        # Poll for result
        for _ in range(30):
            import time; time.sleep(2)
            poll = requests.get(
                f"https://api.replicate.com/v1/predictions/{pred_id}",
                headers={"Authorization": f"Token {api_token}"},
                timeout=15)
            data = poll.json()
            if data["status"] == "succeeded":
                img_url = data["output"][0]
                img = requests.get(img_url, timeout=30)
                return img.content
            elif data["status"] in ("failed", "canceled"):
                return f"Replicate failed: {data.get('error','unknown')}"
        return "Timeout waiting for Replicate"
    except Exception as e:
        return f"Replicate error: {e}"


def _build_prompt(subject: str, style: str, story_genre: str, extra: str) -> str:
    style_tags = _STYLES.get(style, "")
    genre_mood = {
        "Fantasy":   "fantasy setting, magical atmosphere",
        "Sci-Fi":    "science fiction setting, futuristic",
        "Horror":    "dark horror atmosphere, unsettling",
        "Romance":   "warm romantic lighting, emotional",
        "Mystery":   "noir atmosphere, mysterious shadows",
        "Adventure": "epic adventure scene, dynamic composition",
        "Thriller":  "tense dramatic scene, high contrast",
        "Historical": "historical period-accurate setting",
    }.get(story_genre, "literary fiction")
    parts = [p for p in [subject, genre_mood, style_tags, extra] if p]
    return ", ".join(parts)


# ── Main Panel ─────────────────────────────────────────────────────────────
def show_visual_generator(story, characters, ctx=""):
    """Full AI visual generation panel with multi-provider support."""

    st.markdown(
        "<div style='font-size:0.72rem;color:#6B7080;margin-bottom:12px;'>"
        "Generate character portraits, scene illustrations, and cover art. "
        "Your API key is used only for this request and never stored.</div>",
        unsafe_allow_html=True)

    # Provider selection + API key
    provider = st.selectbox("AI Image Provider", list(_PROVIDERS.keys()),
                            key=f"vis_provider_{ctx}")
    prov     = _PROVIDERS[provider]

    key_val = st.text_input(
        prov["key_label"],
        type="password" if "key" in prov["key_label"].lower() else "default",
        placeholder=prov["key_placeholder"],
        key=f"vis_api_key_{ctx}",
        help=f"Get yours at: {prov['docs']}")

    if prov["free"]:
        st.caption(f"✅ Free to use — requires local install. [Setup guide]({prov['docs']})")
    else:
        st.caption(f"Requires paid API key. [Get key]({prov['docs']})")

    st.markdown("---")

    # Generation type
    gen_type = st.radio("Generate",
        ["🧑 Character Portrait", "🏔 Scene Illustration", "📚 Book Cover", "✏️ Custom"],
        horizontal=True, key=f"vis_gen_type_{ctx}", label_visibility="collapsed")

    # Subject builder
    subject = ""
    if gen_type == "🧑 Character Portrait" and characters:
        char_names = [c["name"] for c in characters]
        sel_char   = st.selectbox("Character", char_names, key=f"vis_char_{ctx}")
        char       = next((c for c in characters if c["name"] == sel_char), characters[0])
        age_hint   = st.text_input("Age / physical notes",
            placeholder="e.g. mid-30s, weathered face, green eyes",
            key=f"vis_age_{ctx}")
        subject = (f"portrait of {char['name']}, "
                   f"{char.get('description','a character')[:80]}, "
                   f"{age_hint}")
    elif gen_type == "🧑 Character Portrait":
        st.warning("Add characters in the Cast tab first.")
        return
    elif gen_type == "🏔 Scene Illustration":
        scene_desc = st.text_input("Describe the scene",
            placeholder="e.g. Two figures facing each other across a misty bridge at dawn",
            key=f"vis_scene_{ctx}")
        subject = scene_desc
    elif gen_type == "📚 Book Cover":
        subject = (f"book cover for '{story.get('title','Untitled')}', "
                   f"{story.get('genre','Fiction')} genre, "
                   f"dramatic composition, title text space at top")
    else:
        subject = st.text_area("Custom prompt", height=80, key=f"vis_custom_{ctx}",
                               placeholder="Describe exactly what you want to generate…")

    # Style + extras
    col1, col2 = st.columns(2)
    with col1:
        style = st.selectbox("Art style", list(_STYLES.keys()), key=f"vis_style_{ctx}")
    with col2:
        quality = st.selectbox("Quality / size",
            ["Standard (512px)", "HD (1024px)", "Square (1024x1024)"],
            key=f"vis_quality_{ctx}")

    extra_tags = st.text_input("Additional tags (optional)",
        placeholder="e.g. volumetric lighting, intricate details, trending on artstation",
        key=f"vis_extra_{ctx}")

    negative = st.text_input("Negative prompt (things to avoid)",
        value="blurry, low quality, watermark, text, signature, deformed",
        key=f"vis_negative_{ctx}")

    # Full prompt preview
    if subject:
        full_prompt = _build_prompt(subject, style, story.get("genre", "Fantasy"), extra_tags)
        with st.expander("📋 Full prompt preview"):
            st.code(full_prompt, language=None)

    # Generate
    gen_disabled = not (key_val.strip() and subject.strip())
    if st.button("🎨 Generate Image", key=f"vis_generate_{ctx}",
                 use_container_width=True, disabled=gen_disabled):

        full_prompt = _build_prompt(subject, style, story.get("genre", "Fantasy"), extra_tags)

        with st.spinner("Generating… this may take 15–60 seconds"):
            if provider == "DALL-E 3 (OpenAI)":
                size_map = {"Standard (512px)": "1024x1024",
                            "HD (1024px)": "1024x1792",
                            "Square (1024x1024)": "1024x1024"}
                result = _call_dalle(key_val, full_prompt,
                                     size_map.get(quality, "1024x1024"))
            elif provider == "Stable Diffusion (local)":
                result = _call_sd(key_val, full_prompt, negative)
            else:  # Replicate
                result = _call_replicate(key_val, full_prompt)

        if isinstance(result, bytes):
            st.session_state["vis_last_image"] = result
            st.session_state["vis_last_prompt"] = full_prompt
            st.rerun()
        else:
            st.error(f"Generation failed: {result}")

    # Display result
    if img_bytes := st.session_state.get("vis_last_image"):
        st.image(img_bytes, use_container_width=True)
        title_slug = story.get("title", "story").replace(" ", "_")[:30]
        st.download_button(
            "⬇ Download Image", data=img_bytes,
            file_name=f"{title_slug}_{gen_type.split()[1].lower()}.png",
            mime="image/png", key=f"vis_download_{ctx}",
            use_container_width=True)
        if st.button("🗑 Clear", key=f"vis_clear_{ctx}"):
            st.session_state.pop("vis_last_image", None)
            st.session_state.pop("vis_last_prompt", None)
            st.rerun()
