import asyncio
import threading
from io import BytesIO

import edge_tts
import streamlit as st

st.set_page_config(page_title="Test de voix", layout="centered")

VOICES = {
    # nom affiché : (id de la voix edge-tts, rate, pitch)
    "🎙️ Gemini (Femme)": ("fr-FR-VivienneMultilingualNeural", 0, 0),
    "🎙️ Gemini (Homme)": ("fr-FR-RemyMultilingualNeural", 0, 0),
    "🎙️ Denise (adulte)": ("fr-FR-DeniseNeural", -12, 0),
    "🎙️ Rémy (multilingue)": ("fr-FR-RemyMultilingualNeural", -12, 0),
    "🎙️ Éloïse (enfant)": ("fr-FR-EloiseNeural", -12, 0),
    "🎙️ Henri (jeune)": ("fr-FR-HenriNeural", -5, 25),
}


async def generer_audio(texte, voice, rate, pitch):
    communicate = edge_tts.Communicate(texte, voice, rate=rate, pitch=pitch)
    buffer = BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])
    buffer.seek(0)
    return buffer.read()


def generer_audio_sync(texte, voice, rate, pitch):
    """Thread séparé avec sa propre boucle asyncio (évite le conflit avec Streamlit)."""
    resultat, erreur = {}, {}

    def _run():
        try:
            resultat["audio"] = asyncio.run(generer_audio(texte, voice, rate, pitch))
        except Exception as e:
            erreur["exception"] = e

    thread = threading.Thread(target=_run)
    thread.start()
    thread.join()

    if "exception" in erreur:
        raise erreur["exception"]
    return resultat.get("audio")


st.title("🔊 Test de voix")

voice_label = st.selectbox("Voix", list(VOICES.keys()))
_, rate_def, pitch_def = VOICES[voice_label]

# Les curseurs reprennent les valeurs par défaut de la voix choisie
col1, col2 = st.columns(2)
with col1:
    rate_val = st.slider("Vitesse (%)", -50, 50, rate_def, key=f"rate_{voice_label}")
with col2:
    pitch_val = st.slider("Pitch (Hz)", -50, 50, pitch_def, key=f"pitch_{voice_label}")

texte = st.text_area("Phrase à lire", "Bonjour, ceci est un test de voix.", height=120)

if st.button("🔊 Écouter"):
    if not texte.strip():
        st.warning("Écris une phrase d'abord.")
    else:
        voix_id = VOICES[voice_label][0]
        rate = f"{rate_val:+d}%"
        pitch = f"{pitch_val:+d}Hz"
        try:
            with st.spinner("Génération de la voix..."):
                audio = generer_audio_sync(texte, voix_id, rate, pitch)
            st.audio(audio, format="audio/mp3", autoplay=True)
        except Exception as e:
            st.error(f"Erreur lors de la génération audio : {e}")