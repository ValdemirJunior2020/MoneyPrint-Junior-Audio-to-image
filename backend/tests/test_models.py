from backend.app.models import AudioScene, AudioStoryboard

def test_storyboard_validation():
    sb = AudioStoryboard(title="Test",audio_duration=10,scenes=[AudioScene(scene_number=1,start_seconds=0,end_seconds=10,transcript="hello",visual_description="scene",image_prompt="prompt")])
    assert sb.scenes[0].end_seconds == 10
