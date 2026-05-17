You will make a git commit.
- Read the files and ignore your memory of what changed.
- Git Commit Message Format:
   - **Title**: Use Title Case For Commit Message Titles. Synthetic. Less than 80 characters.
   - **Body**: After the title, write a short 1-2 sentence summary of the purpose and result. Default to plain paragraphs, not bullets.
   - **Sections**: If you use section items, use Unicode bullets like `•` rather than Markdown bullets like `-` or `*`. Optional sections (`WORK`, `WHY`, `DETAIL`, `ALSO`) are allowed only when they add real value, and they must stay short.
   - **Wording**: Prefer direct statements of what changed and why. Avoid contrastive filler like `instead of`, `rather than`, or `no longer` unless the comparison is the important point.
- SYNTHESIZE. The commit subject and opening sentences should tell the reader what changed at a high level and why.
- SUMMARIZE the purpose. Do NOT repeat the code changes line by line or enumerate the diff. We already have the code and file list.
- Only mention file paths if it adds value. The file changes are part of the commit.
- Do not mention Claude/Codex/Gemini as code author unless specifically asked. The human is the author. THERE IS NO CO-AUTHOR, Claude!
- Do NOT wait for confirmation. Just commit immediately.

## EXAMPLE GIT COMMIT MESSAGE

Physics Engine: Knob Braking and Ramp Unified Under Base Class

Shared ramp and braking logic now live in `PhysicsEngineConcreteBase`.

WORK
• KnobSlider and XYPad now delegate to the same braking path.

WHY
• DRY

ALSO
• Renamed `applyFriction` to `applyBraking` so the shared behavior reads the same way it behaves.

## EXAMPLE WITH MULTIPLE WORK ITEMS

Fix AUv3 LCD Font And Build Log

AUv3 now renders the LCD text correctly, and Fastlane makes plist build bumps easier to verify.

WORK
• Register `DigitalLCD.ttf` in the AUv3 extension plists.
• Log the old and new `CFBundleVersion` before plist updates.

WHY
• All three AUv3 bundles were missing LED font.
• Fastlane messages were confusing.

DETAIL
• This combines the runtime fix with the logging cleanup because both touch the same plist and release-versioning path.

ALSO
• Keep the current plist build-number bumps in the same commit when they are part of the same change.
