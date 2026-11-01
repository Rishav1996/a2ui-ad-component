---
name: a2ui-v09-catalog-builder
description: Authors and validates freestanding A2UI v0.9 JSON catalogs, component schemas, and surface payloads following A2UI v0.9 specifications and adjacency-list architecture.
---

# A2UI v0.9 Catalog Builder

## Overview
This skill provides standards and validation rules for authoring A2UI (`v0.9`) component catalogs and surface messages.

## Core Rules & Guardrails

1. **Schema Referencing:**
   - External type references must resolve to canonical common definitions: `https://a2ui.org/specification/v0_9/common_types.json`.
   - Core reusable definitions include:
     - `https://a2ui.org/specification/v0_9/common_types.json#/$defs/CatalogComponentCommon`
     - `https://a2ui.org/specification/v0_9/common_types.json#/$defs/DynamicString`
     - `https://a2ui.org/specification/v0_9/common_types.json#/$defs/Action`
     - `https://a2ui.org/specification/v0_9/common_types.json#/$defs/DynamicBoolean`

2. **AdBanner Component Specification:**
   - Must inherit from `CatalogComponentCommon` (or define `allOf` including common component properties).
   - Properties:
     - `sponsorName`: `DynamicString` (Required) — Brand or sponsor identification.
     - `headline`: `DynamicString` (Required) — Primary promotional message.
     - `bodyText`: `DynamicString` (Optional) — Secondary promotional copy or discount details.
     - `ctaLabel`: `DynamicString` (Required) — Label on action button (e.g. "Learn More", "Claim Credit").
     - `disclosureText`: `DynamicString` (Required) — Regulatory compliance label (e.g., "Sponsored", "Promoted").
     - `mediaUrl`: `DynamicString` (Optional) — Verified HTTPS URL for image/logo banner.
     - `onClickAction`: `Action` (Required) — A2UI Action emitted when the user clicks the banner or CTA button.
     - `badgeColor`: `string` (Optional) — Color token for the disclosure badge.

3. **Flat Adjacency-List Architecture in `createSurface`:**
   - In A2UI v0.9, surfaces do NOT use deeply nested component trees.
   - The surface message contains a flat `components` array where each element has:
     ```json
     {
       "id": "unique_component_id",
       "component": {
         "ComponentName": { ... }
       }
     }
     ```
   - Parent containers refer to child component IDs inside an array (e.g. `children: ["id1", "id2"]`).
   - `createSurface` must specify `surfaceId`, `catalogId` (or `supportedCatalogIds`), and the flat `components` list.

4. **Example Payloads:**
   - Surface payloads must strictly conform to the declared catalog definitions and test cleanly against JSON Schema validators.

