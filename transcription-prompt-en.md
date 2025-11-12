# Transcription

Please transcribe the following audio. Identify speakers and mark the text with timestamps. Follow these rules:

Identify speakers. Use proper names when identifiable. If not identifiable, use Speaker 1, Speaker 2, etc.

Add a timestamp to each paragraph in the format [HH:MM:SS] and place it at the beginning. Do not use fractions of seconds, precision is 1 second. Even if the audio file has fractions. For example, if the audio has [00h:30m:53.777s], write [00h:30m:53s] in the memo.

Put consecutive speech from one speaker under one timestamp. Add a new timestamp only when the speaker changes.

Identify speakers based on how their names are mentioned in the conversation.

Remove all filler words: uh, um, hmm, mhm, aha and other similar ones!!!

Preserve content and meaning. Do not paraphrase. Do not add information.

Use correct spelling. Use normal punctuation.

If a word is unclear, mark it as [??]. If a sentence part is inaudible, mark it as [inaudible].

If two speakers are talking at the same time, mark [talking simultaneously] at that location.

Do not add summaries or meta-comments. Output only the clean transcript.

Output format:

[00h:00m:00s] Speaker 1: Hello. Let's start the meeting. We have three items on the agenda.
[00h:00m:18s] Speaker 2: Hello. I'll add one remark to the first item.
[00h:00m:27s] Speaker 1: Fine. Let's first look at last week's numbers.
[00h:00m:45s] Speaker 2: [??] This report reached me yesterday evening.
[00h:00m:58s] Speaker 3: [talking simultaneously] I'll briefly speak from my perspective.

Now transcribe in the same format.

# Memo
Please create a meeting memo based on this transcription. Write in definitive voice. Keep language simple and correct. Do not use filler words. Do not use conditional mood. Do not add your assumptions.

Rules:

1. Set the meeting title according to the main topics.
2. Date and time are not necessary. Leave blank if unknown.
3. Add a brief summary with 3 to 5 sentences. Purpose and outcome.
4. Divide content by topics. Group into logical themes.
6. Under each topic, describe the discussion. Add timestamp range from transcription.
7. Record decisions. One decision per line. Add decision maker's name. Add timestamp reference.
8. Record Actions. Add responsible person, deadline, brief description, timestamp reference for each action.
9. Record open questions. Add owner, next step, timestamp reference.
10. Record risks or obstacles. Add impact and plan.
11. Record next agreed meetings. Add date, time, purpose.
12. Correct spelling. Keep sentences short. Avoid passive voice.
13. Do not copy transcription word-for-word. Phrase briefly but preserve content and meaning.
14. If information is missing, leave field blank. Do not speculate.
15. Use second precision in timestamps, not fractions of seconds. Even if transcription has fractions. For example, if transcription has [00h:30m:53.777s], write [00h:30m:53s] in memo.

Output format, follow content and markdown format:

# Title: <title>
Date: <YYYY-MM-DD>
Time: [HH:MM-HH:MM](HH:MM-HH:MM)

## Participants
* <Name, role>
* <Name, role>

## Summary
<3-5 sentences. purpose. main outcome. what we decided. what we do next.>

### Topic: <topic name>
Time range: [HH:MM:SS-HH:MM:SS]
* <brief description>
* <important point>
* <important point>

## Decisions
* <decision>: responsible: <name>. Reference: [HH:MM:SS]
* <decision>: responsible: <name>. Reference: [HH:MM:SS]

## Actions
* <action>: <name>, deadline: <date>. Reference: [HH:MM:SS]
* <action>: <name>, deadline: <date>. Reference: [HH:MM:SS]

## Questions
* <question>: <name>. Next step: <step>. Reference: [HH:MM:SS]

## Risks and obstacles
* <risk/obstacle>. Impact: <impact>. Plan: <plan>. Reference: [HH:MM:SS]

## Next meetings
* <date time>
* <purpose>
* <participants if known>