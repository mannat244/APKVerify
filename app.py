# apk_verifier_final.py
import streamlit as st
from apkfile import ApkFile
import tempfile
import os
from google_play_scraper import app, search

def get_app_name_from_dict(details_dict):
    """
    Intelligently extracts a display name from the 'labels' key of the details dictionary.
    """
    labels = details_dict.get('labels', {})
    if labels:
        if 'en' in labels:
            return labels['en']
        return list(labels.values())[0]
    return None

def get_verdict(app_name, version_name, play_details):
    score = 100
    reasons = []
    if play_details is None:
        score -= 50
        reasons.append("❌ **App Not Found on Play Store:** The package name does not exist on the official Google Play Store. This is a major red flag.")
    else:
        # App Name Check
        apk_name_lower = app_name.lower()
        store_name_lower = play_details['title'].lower()
        if apk_name_lower == store_name_lower:
            reasons.append("✅ **App Name Match:** The app name is consistent with the Play Store listing.")
        elif apk_name_lower in store_name_lower or store_name_lower in apk_name_lower:
            score -= 15
            reasons.append(f"⚠️ **Minor Name Mismatch:** APK name is '{app_name}', Play Store name is '{play_details['title']}'.")
        else:
            score -= 40
            reasons.append(f"❌ **Major Name Mismatch:** APK name ('{app_name}') is very different from the Play Store name ('{play_details['title']}').")

        # Version Check
        if version_name == play_details['version']:
            reasons.append(f"✅ **Version Match:** The APK version (`{version_name}`) is the latest available on the Play Store.")
        else:
            score -= 20
            reasons.append(f"⚠️ **Version Mismatch:** APK version is `{version_name}`, but the latest on the Play Store is `{play_details['version']}`. This could be an old or modified version.")
        
        reasons.append(f"✅ **Official Developer:** The developer on the Play Store is **{play_details['developer']}**.")

    # Determine Final Verdict
    if score >= 90:
        st.success("✅ Likely Genuine")
    elif 50 <= score < 90:
        st.warning("⚠️ Potentially Outdated or Modified")
    else:
        st.error("🚨 Potentially Fake or Unofficial")
        
    st.write("#### Analysis:")
    for reason in reasons:
        st.markdown(f"- {reason}")

def handle_comparison(app_name, package_name, version_name):
    st.header("📊 Verification and Analysis")
    try:
        play_details = app(package_name, lang='en', country='us')
        get_verdict(app_name, version_name, play_details)
        st.divider()
        st.write("#### Detailed Comparison:")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📁 Uploaded APK")
            st.info(f"**App Name:** {app_name}")
            st.info(f"**Version:** {version_name}")
        with col2:
            st.subheader("🛒 Play Store Listing")
            st.success(f"**App Name:** {play_details['title']}")
            st.success(f"**Version:** {play_details['version']}")
        st.link_button("View Official Play Store Page", play_details['url'])
    except Exception as e:
        if type(e).__name__ == 'NotFoundError':
            get_verdict(app_name, version_name, None)
            st.divider()
            st.subheader(f"🤔 Searching for Apps Named '{app_name}'...")
            try:
                search_results = search(app_name, n_hits=3, lang='en', country='us')
                if not search_results:
                    st.warning("No similar apps found on the Play Store.")
                else:
                    st.write("Here are the top legitimate apps with a similar name:")
                    for result in search_results:
                        with st.container(border=True):
                            st.markdown(f"**{result['title']}** by *{result['developer']}*")
                            st.text(f"Package: {result['appId']}")
                            # --- THIS IS THE CORRECTED PART ---
                            # Manually construct the URL from the appId
                            play_store_url = f"https://play.google.com/store/apps/details?id={result['appId']}"
                            st.link_button("Go to Play Store Page", play_store_url)
            except Exception as search_e:
                st.error(f"An error occurred during the search: {search_e}")
        else:
            st.error(f"An unexpected error occurred while contacting the Play Store: {e}")

# --- Streamlit UI ---
st.set_page_config(page_title="APK Verifier", page_icon="🛡️", layout="centered")
st.title("🛡️ APK Verifier")
st.write("Upload an APK to verify if it's genuine by comparing it to the Google Play Store.")

uploaded_file = st.file_uploader("Choose an APK file", type=["apk"])

if uploaded_file:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"Successfully uploaded and processing `{uploaded_file.name}`...")
        try:
            # IMPORTANT: Update this path to where aapt.exe is on your system
            apk_file = ApkFile(path=temp_path, aapt_path="aapt")            
            # Use the reliable dictionary method to extract details
            details_dict = apk_file.as_dict()

            # Extract data from the dictionary using the CORRECT keys.
            package_name = details_dict.get('package_name')
            version_name = details_dict.get('version_name')
            # Intelligently find the app name from the 'labels' dictionary within.
            app_name = get_app_name_from_dict(details_dict)

            if not all([app_name, package_name, version_name]):
                st.error("Fatal Error: Could not extract essential details (app name, package name, or version) from the APK. The APK may be corrupt or malformed.")
                st.write("Below is the raw data that could be extracted for debugging:")
                st.json(details_dict)
            else:
                handle_comparison(app_name, package_name, version_name)
                with st.expander("Show All Raw APK Details"):
                    st.json(details_dict)
        except Exception as e:
            st.error(f"❌ An error occurred while processing the APK: {e}")