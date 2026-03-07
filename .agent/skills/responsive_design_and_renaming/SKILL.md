---
name: Cloud Run Responsiveness & Rename Guide
description: Guide for re-implementing mobile responsiveness, viewport fixes, and service renaming for Cloud Run deployment.
---

# Cloud Run Responsiveness & Rename Guide

This guide captures the changes required to:
1.  Make the Sidebar mobile-responsive (Drawer pattern).
2.  Fix Viewport Height on mobile (preventing scroll-past-input).
3.  Rename the application services and UI branding to "Selo".
4.  Fix Backend Vertex AI Model Mapping for Cloud Run (ADC).

## 1. Mobile Responsiveness (Sidebar)

### `apps/web/components/Sidebar.tsx`

Transform the sidebar into a fixed overlay on mobile.

**Key Changes:**
- Use a `fixed inset-y-0 left-0 z-50` container.
- Add a backdrop overlay (`fixed inset-0 bg-black/50 z-40`) visible only when sidebar is open on mobile.
- Use `transform transition-transform` to slide in/out.
- Add a Close button inside the sidebar for mobile users.

**Snippet (Structure):**
```tsx
const Sidebar = ({ ... }) => {
    // ...
    return (
        <>
            {/* Mobile Overlay Backdrop */}
            {isOpen && (
                <div 
                    className="md:hidden fixed inset-0 bg-black/50 z-40"
                    onClick={toggleSidebar}
                />
            )}

            {/* Sidebar Container */}
            <div 
                className={`
                    fixed inset-y-0 left-0 z-50 flex flex-col h-full 
                    w-64 bg-[#1e1f20] border-r border-[#333537] 
                    transform transition-transform duration-300 ease-in-out
                    ${isOpen ? "translate-x-0" : "-translate-x-full"} 
                    md:translate-x-0 
                    ${isOpen ? "w-64" : "w-64 md:w-16"}
                `}
            >
               {/* Mobile Header with Close Button */}
               <div className="md:hidden flex items-center justify-between p-4 border-b border-[#333537]">
                    <span className="font-semibold text-white">Menu</span>
                    <button onClick={toggleSidebar}>
                        <X className="w-5 h-5 text-gray-400" />
                    </button>
               </div>
               {/* ... Rest of Sidebar content ... */}
            </div>
        </>
    );
};
```

### `apps/web/app/page.tsx` (Layout)

Adjust the main content margin to respect sidebar width on Desktop, but be full-width on Mobile.

**Key Changes:**
- Remove `ml-64` / `ml-16` on mobile (use `ml-0`).
- Use `md:ml-64` / `md:ml-16` for desktop.
- **Header:** Add a mobile-only header bar with Hamburger menu.

**Snippet (Header):**
```tsx
{/* Mobile Header */}
<div className="md:hidden flex items-center px-4 py-3 border-b border-[#333537] bg-[#1e1f20]">
    <button onClick={() => setIsSidebarOpen(true)} className="p-2 -ml-2 mr-2 text-gray-400">
        <Menu className="w-6 h-6" />
    </button>
    <span className="text-lg font-medium text-gray-200">Selo</span> {/* Start with 'Selo' */}
    <div className="w-10" /> {/* Spacer to center title if needed */}
</div>
```

**Snippet (Main Container):**
```tsx
<main 
    className={`
        flex-1 h-full flex flex-col relative transition-all duration-300 ease-in-out
        ${isSidebarOpen ? "md:ml-64" : "md:ml-16"} 
        w-full md:w-auto
    `}
>
   {/* ChatInterface */}
</main>
```

---

## 2. Mobile Viewport Fix (Scrolling)

To prevent mobile browsers from scrolling past the input due to URL bars (100vh issue):

### `apps/web/app/page.tsx` (Root)

Use `h-dvh` (Dynamic Viewport Height) if supported, or stick to `fixed inset-0` as a robust alternative (though `fixed inset-0` disables body scroll, which is good for chat apps).

**Recommended Fix:**
```tsx
// Option A: Dynamic Height (Allows body scroll if content overflows, but requires h-full chain)
<div className="flex h-dvh md:h-screen bg-[#131314]">

// Option B: Fixed Inset (Locks app to viewport, requires internal scroll)
// <div className="flex fixed inset-0 bg-[#131314]">
```

---

## 3. Renaming Services & Branding ("Selo")

### Deployment Script (`deploy_cloud_run.sh`)
Update service names to reflect new branding.

```bash
# ...
gcloud builds submit --tag gcr.io/$PROJECT_ID/selo-backend ./apps/agent
gcloud run deploy selo-backend ...

gcloud builds submit --tag gcr.io/$PROJECT_ID/selo-web ./apps/web
gcloud run deploy selo-web ...
```

### Metadata (`apps/web/app/layout.tsx`)
Update title and description.
```tsx
export const metadata: Metadata = {
  title: "Selo - Looker Coaching Agent",
  description: "AI-powered analytics assistant",
  // ...
};
```

### UI Header (`page.tsx`)
Update displayed name in Mobile Header (see Section 1).

---

## 4. Critical Backend Fix (Cloud Run 404 Error)

When deploying to Cloud Run, the backend uses **Application Default Credentials (ADC)**. The default logic in `mcp_agent.py` missed the model mapping step for ADC, causing raw model strings (e.g. `claude-sonnet-4-5...`) to be sent to Vertex AI, resulting in **404 Publisher Model Not Found**.

### `apps/agent/mcp_agent.py`

**Fix:** Add `self.model_name = self._map_to_vertex_model(model_name)` to the ADC fallback block.

```python
            elif _AnthropicVertex and _gcp_project: # Fallback to ADC if explicitly requested or defaults
                 # CRITICAL FIX: Map model name!
                 # Ensure custom IDs like 'claude-sonnet-4-5' are mapped to valid Vertex IDs that the Service Account has ACCESS to.
                 # Example: "claude-sonnet-4-5" -> "claude-sonnet-4-5@20250929"
                 # NOTE: Identity (JSON Key) != Permission. Service Account must be whitelisted for the specific Model ID.
                 self.model_name = self._map_to_vertex_model(model_name)
                 
                 self.client = _AnthropicVertex(
                    project_id=_gcp_project,
                    region=_gcp_region_claude,
                 )
                 self.is_vertex = True

## 5. Dockerfile Fix for Cloud Run

Ensure `apps/agent/Dockerfile` does **not** override environment variables or force a local key path, which breaks Cloud Run's native authentication.

```dockerfile
# COMMENT OUT these lines:
# ENV GOOGLE_APPLICATION_CREDENTIALS="/app/sa-key.json"
# ENV GOOGLE_API_KEY=""
# ...
```
```
