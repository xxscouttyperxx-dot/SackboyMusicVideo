# Collection Visibility Fix + Retry Push v1

## Why this exists
The collection organization pass succeeded locally, but its log showed visible objects changed from 204 to 205. That means one object that had previously been hidden by collection visibility became effectively visible after being moved into the new clean collection structure.

## Fix
- Set `08_HIDDEN_NONVISIBLE_REVIEW` collection `hide_viewport=True`.
- Set `08_HIDDEN_NONVISIBLE_REVIEW` collection `hide_render=True`.
- Set objects inside that collection to `hide_select=True`.

## Safety
- No objects deleted.
- No visible character/clothing/scene objects intentionally changed.
- No geometry, material, modifier, shape-key, light, or camera changes.

## Counts
- Total objects before/after: 252 -> 252
- Visible objects before/after: 205 -> 205
- Hidden objects before/after: 47 -> 47

## Push note
The previous push failed after the local commit was created. This package creates a small visibility-fix commit on top and uses a longer retry loop for Git LFS/network failures.