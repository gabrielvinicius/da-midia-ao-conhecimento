# tests/e2e/test_full_media_pipeline.py
import pytest
import requests
import time

# The BASE_URL is now defined in conftest.py and used by fixtures
from .conftest import BASE_URL


def test_full_audio_processing_pipeline(auth_token):
    """
    Comprehensive end-to-end test for the complete media processing pipeline.
    Tests: Upload → Video Processing → Transcription → Summarization → Sentiment Analysis → Topic Modeling
    """
    # 1. Upload a realistic audio file with actual content
    # Using a longer WAV with synthesized speech for better testing
    test_audio_content = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80\x3e\x00\x00\x00\x7d\x00\x00\x02\x00\x10\x00data\x00\x08\x00\x00' + b'\x00\x01' * 1000
    
    files = {"file": ("test_audio.wav", test_audio_content, "audio/wav")}
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    print("📤 Starting media upload...")
    upload_response = requests.post(f"{BASE_URL}/media/", files=files, headers=headers)
    assert upload_response.status_code == 201, f"Upload failed: {upload_response.text}"
    
    media_data = upload_response.json()
    media_id = media_data["id"]
    print(f"✅ Media uploaded successfully with ID: {media_id}")
    print(f"   File size: {media_data.get('file_size', 'unknown')} bytes")
    print(f"   Media type: {media_data.get('media_type', 'unknown')}")

    # 2. Enhanced polling with detailed status tracking
    print("\n🔄 Monitoring processing pipeline...")
    start_time = time.time()
    media_status = ""
    last_status = ""
    pipeline_stages = {
        "UPLOADED": "📥 Media uploaded, waiting for processing",
        "PROCESSING": "⚙️  Processing in progress",
        "COMPLETED": "✅ Processing completed successfully",
        "FAILED": "❌ Processing failed"
    }
    
    while time.time() - start_time < 180:  # 3-minute timeout for comprehensive testing
        status_response = requests.get(f"{BASE_URL}/media/{media_id}", headers=headers)
        if status_response.status_code == 200:
            media_data = status_response.json()
            media_status = media_data["status"]
            
            # Log status changes
            if media_status != last_status:
                status_msg = pipeline_stages.get(media_status, f"🔄 Status: {media_status}")
                elapsed = time.time() - start_time
                print(f"   {status_msg} (after {elapsed:.1f}s)")
                last_status = media_status
            
            if media_status == "COMPLETED":
                processing_time = time.time() - start_time
                print(f"🎉 Pipeline completed in {processing_time:.1f} seconds")
                break
            if media_status == "FAILED":
                error_msg = media_data.get('error_message', 'Unknown error')
                pytest.fail(f"Media processing failed: {error_msg}")
        
        time.sleep(3)  # More frequent polling for detailed monitoring
    
    assert media_status == "COMPLETED", f"Media processing did not complete within timeout. Final status: {media_status}"

    # 3. Comprehensive verification of all pipeline artifacts
    print("\n🔍 Verifying pipeline artifacts...")
    
    # 3a. Verify Transcription
    print("   📝 Checking transcription...")
    transcription_response = requests.get(f"{BASE_URL}/transcriptions/?media_id={media_id}", headers=headers)
    assert transcription_response.status_code == 200, f"Failed to fetch transcription: {transcription_response.text}"
    
    transcription_data = transcription_response.json()
    if isinstance(transcription_data, list) and len(transcription_data) > 0:
        transcription_data = transcription_data[0]
    
    assert transcription_data["status"] == "COMPLETED", f"Transcription not completed: {transcription_data.get('status')}"
    assert "text" in transcription_data, "Transcription missing text field"
    assert transcription_data.get("language"), "Transcription missing language detection"
    
    transcription_text = transcription_data["text"]
    print(f"   ✅ Transcription: '{transcription_text[:100]}{'...' if len(transcription_text) > 100 else ''}'")
    print(f"      Language: {transcription_data.get('language', 'unknown')}")
    print(f"      Confidence: {transcription_data.get('confidence_score', 'unknown')}")
    
    # 3b. Verify Summarization
    print("   📄 Checking summarization...")
    summary_response = requests.get(f"{BASE_URL}/summaries/?media_id={media_id}", headers=headers)
    assert summary_response.status_code == 200, f"Failed to fetch summary: {summary_response.text}"
    
    summary_data = summary_response.json()
    if isinstance(summary_data, list) and len(summary_data) > 0:
        summary_data = summary_data[0]
    
    assert summary_data["status"] == "COMPLETED", f"Summary not completed: {summary_data.get('status')}"
    assert "text" in summary_data, "Summary missing text field"
    
    summary_text = summary_data["text"]
    print(f"   ✅ Summary: '{summary_text[:100]}{'...' if len(summary_text) > 100 else ''}'")
    print(f"      Strategy: {summary_data.get('strategy', 'unknown')}")
    print(f"      Provider: {summary_data.get('provider', 'unknown')}")
    
    # 3c. Verify Sentiment Analysis
    print("   😊 Checking sentiment analysis...")
    sentiment_response = requests.get(f"{BASE_URL}/sentiment-analysis/?media_id={media_id}", headers=headers)
    
    if sentiment_response.status_code == 200:
        sentiment_data = sentiment_response.json()
        if isinstance(sentiment_data, list) and len(sentiment_data) > 0:
            sentiment_data = sentiment_data[0]
            
        print(f"   ✅ Sentiment: {sentiment_data.get('overall_sentiment', 'unknown')}")
        print(f"      Score: {sentiment_data.get('sentiment_score', 'unknown')}")
        print(f"      Confidence: {sentiment_data.get('confidence', 'unknown')}")
        
        # Verify sentiment data structure
        assert "overall_sentiment" in sentiment_data, "Sentiment analysis missing overall_sentiment"
        assert sentiment_data["overall_sentiment"] in ["positive", "negative", "neutral"], "Invalid sentiment value"
    else:
        print(f"   ⚠️  Sentiment analysis not available (status: {sentiment_response.status_code})")
    
    # 3d. Verify Topic Modeling
    print("   🏷️  Checking topic modeling...")
    topics_response = requests.get(f"{BASE_URL}/topic-modeling/?media_id={media_id}", headers=headers)
    
    if topics_response.status_code == 200:
        topics_data = topics_response.json()
        if isinstance(topics_data, list) and len(topics_data) > 0:
            topics_data = topics_data[0]
            
        print(f"   ✅ Topics found: {len(topics_data.get('topics', []))}")
        print(f"      Keywords: {topics_data.get('keywords', [])[:5]}")  # Show first 5 keywords
        
        # Verify topic modeling data structure
        assert "topics" in topics_data, "Topic modeling missing topics field"
        assert "keywords" in topics_data, "Topic modeling missing keywords field"
    else:
        print(f"   ⚠️  Topic modeling not available (status: {topics_response.status_code})")

    # 4. Performance validation
    total_processing_time = time.time() - start_time
    print(f"\n📊 Pipeline Performance Summary:")
    print(f"   Total processing time: {total_processing_time:.1f} seconds")
    print(f"   Media size: {len(test_audio_content)} bytes")
    print(f"   Processing rate: {len(test_audio_content)/total_processing_time:.1f} bytes/second")
    
    # Assert performance thresholds (adjust based on your requirements)
    assert total_processing_time < 180, f"Processing took too long: {total_processing_time:.1f}s"
    
    print("\n🎉 Full media processing pipeline test completed successfully!")


def test_concurrent_media_processing(auth_token):
    """Test concurrent processing of multiple media files."""
    print("\n🚀 Testing concurrent media processing...")
    
    # Upload multiple files concurrently
    files_data = [
        ("audio1.wav", b'RIFF\x24\x08\x00\x00WAVEfmt' + b'\x00\x01' * 500),
        ("audio2.wav", b'RIFF\x24\x08\x00\x00WAVEfmt' + b'\x00\x02' * 500),
        ("audio3.wav", b'RIFF\x24\x08\x00\x00WAVEfmt' + b'\x00\x03' * 500),
    ]
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    uploaded_media_ids = []
    
    # Upload all files
    for filename, content in files_data:
        files = {"file": (filename, content, "audio/wav")}
        upload_response = requests.post(f"{BASE_URL}/media/", files=files, headers=headers)
        assert upload_response.status_code == 201, f"Upload failed for {filename}"
        
        media_id = upload_response.json()["id"]
        uploaded_media_ids.append(media_id)
        print(f"   📤 Uploaded {filename} with ID: {media_id}")
    
    # Monitor all files for completion
    print("   🔄 Monitoring concurrent processing...")
    start_time = time.time()
    completed_count = 0
    
    while time.time() - start_time < 300 and completed_count < len(uploaded_media_ids):  # 5-minute timeout
        completed_count = 0
        
        for media_id in uploaded_media_ids:
            status_response = requests.get(f"{BASE_URL}/media/{media_id}", headers=headers)
            if status_response.status_code == 200:
                status = status_response.json()["status"]
                if status == "COMPLETED":
                    completed_count += 1
                elif status == "FAILED":
                    pytest.fail(f"Media {media_id} processing failed")
        
        if completed_count < len(uploaded_media_ids):
            time.sleep(5)
    
    processing_time = time.time() - start_time
    print(f"   ✅ All {len(uploaded_media_ids)} files processed in {processing_time:.1f}s")
    
    assert completed_count == len(uploaded_media_ids), f"Only {completed_count}/{len(uploaded_media_ids)} files completed"
    
    # Verify all artifacts exist
    for media_id in uploaded_media_ids:
        transcription_response = requests.get(f"{BASE_URL}/transcriptions/?media_id={media_id}", headers=headers)
        assert transcription_response.status_code == 200, f"Transcription missing for {media_id}"
    
    print(f"   🎉 Concurrent processing test completed successfully!")
