# Video Transcriber

AI-powered video transcription tool. Upload videos and generate accurate, timestamped transcripts using OpenAI Whisper, Faster-Whisper, or other speech-to-text models.

## Features (Planned / In Progress)

- 📁 Video upload (MP4, MOV, WebM, etc.)
- 🎧 Automatic audio extraction
- 🤖 High-accuracy transcription with Whisper
- ⏱️ Timestamped segments
- 🌐 Multi-language support + auto language detection
- 📝 Export as TXT, SRT, VTT, or JSON
- 💻 Clean web UI (Next.js + Tailwind)
- 🔐 Optional local processing with Faster-Whisper for privacy

## Tech Stack

- **Frontend / Full-stack**: Next.js 15 (App Router) + TypeScript + Tailwind CSS + shadcn/ui
- **Transcription**: OpenAI Whisper API (or local Faster-Whisper / Transformers.js)
- **File handling**: Uploadthing or local storage + FFmpeg for audio extraction
- **Deployment**: Vercel

## Getting Started

### Prerequisites
- Node.js 20+
- OpenAI API key (or local Whisper setup)

### Installation

```bash
git clone https://github.com/idris81ahmad-cyber/video-transcriber.git
cd video-transcriber
npm install
```

Copy `.env.example` to `.env.local` and add your keys:

```env
OPENAI_API_KEY=sk-...
```

Then run:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Roadmap

- [ ] Basic file upload + transcription endpoint
- [ ] Audio extraction with FFmpeg
- [ ] Timestamped SRT/VTT export
- [ ] Progress UI and real-time status
- [ ] Local Faster-Whisper option
- [ ] Batch processing
- [ ] Speaker diarization

## License

MIT
