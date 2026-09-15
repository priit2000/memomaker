// Sources checked 2026-09-15. Unknown limits must never be treated as unlimited.
const audioModelCatalog = {
  "deepgram/nova-3": {
    "specialist": true
  },
  "fish-audio/transcribe-1": {
    "specialist": true
  },
  "google/chirp-3": {
    "specialist": true
  },
  "google/gemini-2.5-flash": {
    "specialist": false
  },
  "google/gemini-2.5-flash-lite": {
    "specialist": false
  },
  "google/gemini-2.5-flash-lite:batch": {
    "specialist": false
  },
  "google/gemini-2.5-flash:batch": {
    "specialist": false
  },
  "google/gemini-2.5-pro": {
    "specialist": false
  },
  "google/gemini-2.5-pro-preview": {
    "specialist": false
  },
  "google/gemini-2.5-pro:batch": {
    "specialist": false
  },
  "google/gemini-3-flash-preview": {
    "specialist": false
  },
  "google/gemini-3-flash-preview:batch": {
    "specialist": false
  },
  "google/gemini-3.1-flash-lite": {
    "specialist": false
  },
  "google/gemini-3.1-flash-lite-preview": {
    "specialist": false
  },
  "google/gemini-3.1-flash-lite:batch": {
    "specialist": false
  },
  "google/gemini-3.1-pro-preview": {
    "specialist": false
  },
  "google/gemini-3.1-pro-preview-customtools": {
    "specialist": false
  },
  "google/gemini-3.1-pro-preview:batch": {
    "specialist": false
  },
  "google/gemini-3.5-flash": {
    "specialist": false
  },
  "google/gemini-3.5-flash-lite": {
    "specialist": false
  },
  "google/gemini-3.5-flash-lite:batch": {
    "specialist": false
  },
  "google/gemini-3.5-flash:batch": {
    "specialist": false
  },
  "google/gemini-3.6-flash": {
    "specialist": false
  },
  "google/gemini-3.6-flash:batch": {
    "specialist": false
  },
  "google/gemini-3.7-flash": {
    "specialist": false
  },
  "google/gemini-3.7-flash:batch": {
    "specialist": false
  },
  "google/gemini-3.8-flash": {
    "specialist": false
  },
  "google/gemini-3.8-flash:batch": {
    "specialist": false
  },
  "meta/muse-spark-1.1": {
    "specialist": false
  },
  "meta/muse-spark-1.2": {
    "specialist": false
  },
  "meta/muse-spark-1.2-contributor": {
    "specialist": false
  },
  "meta/muse-spark-1.3": {
    "specialist": false
  },
  "meta/muse-spark-1.3-contributor": {
    "specialist": false
  },
  "meta/muse-voice-transcribe-1.0": {
    "specialist": true
  },
  "microsoft/mai-transcribe-1.5": {
    "specialist": true
  },
  "microsoft/mai-transcribe-2": {
    "specialist": true
  },
  "mistralai/voxtral-mini-3b-2507": {
    "specialist": true
  },
  "mistralai/voxtral-mini-transcribe": {
    "specialist": true
  },
  "mistralai/voxtral-small-24b-2507": {
    "specialist": false
  },
  "mistralai/voxtral-small-24b-2507-stt": {
    "specialist": true
  },
  "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": {
    "specialist": false
  },
  "nvidia/nemotron-3.5-asr-streaming-multilingual-0.6b": {
    "specialist": true
  },
  "nvidia/parakeet-tdt-0.6b-v3": {
    "specialist": true
  },
  "openai/gpt-4o-mini-transcribe": {
    "specialist": true
  },
  "openai/gpt-4o-transcribe": {
    "specialist": true
  },
  "openai/gpt-audio": {
    "specialist": false
  },
  "openai/gpt-audio-mini": {
    "specialist": false
  },
  "openai/gpt-transcribe": {
    "specialist": true
  },
  "openai/whisper-1": {
    "specialist": true
  },
  "openai/whisper-large-v3": {
    "specialist": true
  },
  "openai/whisper-large-v3-turbo": {
    "specialist": true
  },
  "openrouter/auto": {
    "specialist": false
  },
  "openrouter/auto-beta": {
    "specialist": false
  },
  "qwen/qwen3-asr-0.6b": {
    "specialist": true
  },
  "qwen/qwen3-asr-1.7b": {
    "specialist": true
  },
  "qwen/qwen3-asr-flash-2026-02-10": {
    "specialist": true
  },
  "thinkingmachines/inkling": {
    "specialist": false
  },
  "thinkingmachines/inkling-small": {
    "specialist": false
  },
  "thinkingmachines/inkling-small:batch": {
    "specialist": false
  },
  "thinkingmachines/inkling-small:free": {
    "specialist": false
  },
  "thinkingmachines/inkling:batch": {
    "specialist": false
  },
  "thinkingmachines/inkling:free": {
    "specialist": false
  },
  "x-ai/grok-stt-1.0": {
    "specialist": true
  },
  "xiaomi/mimo-v2.5": {
    "specialist": false
  },
  "~google/gemini-flash-latest": {
    "specialist": false
  },
  "~google/gemini-pro-latest": {
    "specialist": false
  }
};
function audioLimits(provider, model, method='inline') {
 const notes=['MemoMaker accepts audio files up to 100 MiB.'];
 const sources=[];
 const add=(label,url)=>sources.push({label,url});
 if(provider==='Google Gemini') {
  notes.push('Gemini audio guide: up to 9.5 hours per prompt; model context and output limits also apply.');
  notes.push(method==='upload'?'Files API: 2 GB per file; MemoMaker still caps files at 100 MiB.':method==='auto'?'Auto uploads files at 20 MiB or above. Smaller files use Inline.':'Inline: audio guide lists 20 MB total request size, including prompts. Google’s newer file guide lists 100 MB; these published limits conflict. Use Upload for large audio.');
  add('Google audio limits','https://ai.google.dev/gemini-api/docs/generate-content/audio');
  add('Google file limits','https://ai.google.dev/gemini-api/docs/files');
 } else if(provider==='OpenRouter') {
  const row=audioModelCatalog[model];
  notes.push('Exact OpenRouter file-size and duration limits: not published in the model endpoint catalog.');
  if(row?.specialist) {
   notes.push('Transcription processing timeout: 60 seconds upstream; this is processing time, not recording length. MemoMaker uses base64 JSON; the 25 MB multipart limit does not describe this upload method.');
   add('OpenRouter transcription limits','https://openrouter.ai/docs/guides/overview/multimodal/stt');
  } else {
   notes.push(row?'Audio input shares the model context window with the prompt. Upstream provider restrictions also apply.':'Model not in the checked audio catalog. Refresh the model list to check availability.');
   add('OpenRouter audio documentation','https://openrouter.ai/docs/guides/overview/multimodal/audio');
  }
  if(model==='microsoft/mai-transcribe-2') {
   notes.push('Speaker identification is enabled. Microsoft reports failures for recordings about 15 minutes or longer. A 33.2 MB file was rejected through OpenRouter; the exact size cutoff is undisclosed.');
   add('Microsoft recording-length restriction','https://learn.microsoft.com/en-us/azure/ai-services/speech-service/mai-transcribe');
  }
  if(model==='openai/whisper-1') {
   notes.push('OpenRouter’s Whisper 1 model description lists a 25 MB audio-file limit.');
   add('Whisper 1 model information','https://openrouter.ai/openai/whisper-1');
  }
  if(/^mistralai\/voxtral-(mini-3b-2507|small-24b-2507|small-24b-2507-stt)$/.test(model)) {
   notes.push('Mistral model capability: up to 30 minutes for transcription. OpenRouter’s serving provider can impose lower limits.');
   add('Mistral Voxtral limits','https://mistral.ai/news/voxtral/');
  }
 } else {
  notes.push('Custom API limits depend on your server and deployment. File size and duration limits are not available from the compatible model-list API.');
 }
 return {notes,sources};
}
function showAudioLimits(host,provider,model,method) {
 host.replaceChildren();
 const {notes,sources}=audioLimits(provider,model,method);
 for(const note of notes){const p=document.createElement('p');p.textContent=note;host.append(p);}
 const details=document.createElement('details');
 const summary=document.createElement('summary');summary.textContent='Sources · checked 15 September 2026';details.append(summary);
 for(const source of sources){const link=document.createElement('a');link.href=source.url;link.textContent=source.label;link.onclick=e=>{e.preventDefault();api('open_link',source.url);};details.append(link);}
 if(sources.length)host.append(details);
}
