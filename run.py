from src.pipeline import SyntheticRadioHost

# Initialize the pipeline
radio_host = SyntheticRadioHost()

# Generate radio show from Wikipedia article
result = radio_host.generate(
    topic="Mumbai Indians",
    duration_minutes=2,
    output_path="output\\mumbai_indians_show.mp3"
)

print(f"Audio saved to: {result.output_path}")