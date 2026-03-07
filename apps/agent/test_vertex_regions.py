import os
import asyncio
from google.auth import default
from google.cloud import aiplatform

# User's target models
MODELS_TO_TEST = [
    "claude-sonnet-4-6@defaultclaude",
    "claude-opus-4-6@defaultclaude",
    "claude-sonnet-4-5@20250929"
]

# Regions to test
REGIONS = ["europe-west1", "us-east5", "us-central1"] # 'global' is not a valid endpoint for prediction, usually

async def test_region(project_id, region):
    print(f"\n--- Testing Region: {region} ---")
    try:
        aiplatform.init(project=project_id, location=region)
        
        # We can't easily "list" publisher models by arbitrary ID without trying to get them
        # simulating a prediction request logic or checking model existence
        from vertexai.preview.generative_models import GenerativeModel
        import vertexai
        vertexai.init(project=project_id, location=region)

        for m_id in MODELS_TO_TEST:
            print(f"Checking {m_id} in {region}...")
            try:
                # Just trying to instantiate might not fail until prediction
                # But let's try to get model info if possible or run a dummy prediction
                model = GenerativeModel(m_id)
                # We need to run a prediction to truly know if 404
                resp = await model.generate_content_async("Hello")
                print(f"✅ SUCCESS: {m_id} works in {region}!")
                return region 
            except Exception as e:
                err_str = str(e)
                if "404" in err_str or "not found" in err_str.lower():
                    print(f"❌ {m_id} NOT FOUND in {region}")
                else:
                    print(f"⚠️  {m_id} Error in {region}: {err_str}")
                    # If it's auth error, we might fail everywhere. If it's 404, it's region specific.
    except Exception as e:
        print(f"Failed to init region {region}: {e}")
    return None

async def main():
    creds, project_id = default()
    print(f"Project: {project_id}")
    
    # We want to find ONE region that works for ALL if possible, or at least the Sonnet one
    
    for region in REGIONS:
        success_region = await test_region(project_id, region)
        if success_region:
            print(f"\n🎉 FOUND WORKING REGION: {success_region}")
            # We could stop here, or check if others work too. 
            # But user wants 'the one working'.
            
if __name__ == "__main__":
    asyncio.run(main())
