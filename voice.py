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
    # Voix anglaises (à utiliser avec un texte en anglais)
    "🇺🇸 Aria (USA, femme)": ("en-US-AriaNeural", 0, 0),
    "🇺🇸 Guy (USA, homme)": ("en-US-GuyNeural", 0, 0),
    "🇬🇧 Sonia (UK, femme)": ("en-GB-SoniaNeural", 0, 0),
    "🇬🇧 Ryan (UK, homme)": ("en-GB-RyanNeural", 0, 0),
}

# edge-tts ne propose pas de vrais styles émotionnels : l'émotion est
# simulée en ajoutant des écarts de vitesse, de pitch et de volume.
# nom : (écart vitesse en %, écart pitch en Hz, volume en %)
EMOTIONS = {
    "⚙️ Custom": (0, 0, 0),  # aucun écart : seuls tes curseurs comptent
    "😐 Neutre": (0, 0, 0),
    "😄 Joyeux": (+10, +15, +10),
    "😢 Triste": (-20, -15, -15),
    "😠 Colère": (+10, -5, +30),
    "😌 Calme": (-15, -5, -10),
    "🤩 Excité": (+25, +25, +20),
    "🕵️ Mystérieux": (-20, -10, -20),
}


async def generer_audio(texte, voice, rate, pitch, volume):
    communicate = edge_tts.Communicate(
        texte, voice, rate=rate, pitch=pitch, volume=volume
    )
    buffer = BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])
    buffer.seek(0)
    return buffer.read()


def generer_audio_sync(texte, voice, rate, pitch, volume):
    """Thread séparé avec sa propre boucle asyncio (évite le conflit avec Streamlit)."""
    resultat, erreur = {}, {}

    def _run():
        try:
            resultat["audio"] = asyncio.run(
                generer_audio(texte, voice, rate, pitch, volume)
            )
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

emotion_label = st.selectbox("Émotion", list(EMOTIONS.keys()))
d_rate, d_pitch, d_volume = EMOTIONS[emotion_label]

# Les curseurs reprennent les valeurs par défaut de la voix choisie
col1, col2 = st.columns(2)
with col1:
    rate_val = st.slider("Vitesse (%)", -50, 50, rate_def, key=f"rate_{voice_label}")
with col2:
    pitch_val = st.slider("Pitch (Hz)", -50, 50, pitch_def, key=f"pitch_{voice_label}")

# Réglages finaux = curseurs + écarts de l'émotion (bornés pour rester valides)
rate_final = max(-90, min(100, rate_val + d_rate))
pitch_final = max(-100, min(100, pitch_val + d_pitch))
volume_final = max(-90, min(100, d_volume))

st.caption(
    f"Réglages envoyés : vitesse {rate_final:+d}% · pitch {pitch_final:+d}Hz · "
    f"volume {volume_final:+d}%"
)

texte = st.text_area("Phrase à lire", "Bonjour, ceci est un test de voix.", height=120)

if st.button("🔊 Écouter"):
    if not texte.strip():
        st.warning("Écris une phrase d'abord.")
    else:
        voix_id = VOICES[voice_label][0]
        try:
            with st.spinner("Génération de la voix..."):
                audio = generer_audio_sync(
                    texte,
                    voix_id,
                    f"{rate_final:+d}%",
                    f"{pitch_final:+d}Hz",
                    f"{volume_final:+d}%",
                )
            # On garde l'audio en mémoire : sans ça, il disparaît dès qu'on
            # clique sur "Télécharger" (Streamlit relance le script).
            st.session_state.audio_bytes = audio
            st.session_state.audio_autoplay = True
        except Exception as e:
            st.error(f"Erreur lors de la génération audio : {e}")

if st.session_state.get("audio_bytes"):
    st.audio(
        st.session_state.audio_bytes,
        format="audio/mp3",
        autoplay=st.session_state.get("audio_autoplay", False),
    )
    st.session_state.audio_autoplay = False

    st.download_button(
        "⬇️ Télécharger le MP3",
        data=st.session_state.audio_bytes,
        file_name="voix.mp3",
        mime="audio/mpeg",
    )
