import sys
import os
import difflib

# Add src to path to allow importing from the project's own utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils import decode_base64_text


def verify_subscription_files(plain_path, base64_path):
    """
    Verifies that the decoded base64 subscription matches the plain-text version.
    This is the ultimate self-verification gate for the CI/CD pipeline.
    """
    print("--- Running Self-Verification Gate ---")
    print(f"Plain-text file: {plain_path}")
    print(f"Base64 file: {base64_path}")

    try:
        with open(plain_path, "r", encoding="utf-8") as f:
            plain_content = f.read()
    except FileNotFoundError:
        print(f"Error: Plain-text file for verification not found at {plain_path}")
        sys.exit(1)

    try:
        with open(base64_path, "r", encoding="utf-8") as f:
            base64_content = f.read()
    except FileNotFoundError:
        print(f"Error: Base64 file for verification not found at {base64_path}")
        sys.exit(1)

    print("Decoding base64 content using project utility...")
    decoded_content = decode_base64_text(base64_content)

    if decoded_content is None:
        print("Fatal Error: Failed to decode base64 content. Verification failed.")
        sys.exit(1)

    # Normalize line endings to prevent cross-platform (Windows/Linux) diff issues
    plain_content_normalized = plain_content.replace("\r\n", "\n").strip()
    decoded_content_normalized = decoded_content.replace("\r\n", "\n").strip()

    if plain_content_normalized == decoded_content_normalized:
        print("Success: Decoded base64 content perfectly matches plain-text content.")
        print("Output integrity is 100% verified.")
        sys.exit(0)
    else:
        print(
            "Fatal Error: Mismatch found between decoded base64 and plain-text content."
        )
        print(
            "Self-Verification Gate has FAILED. Stopping pipeline to prevent corrupted deployment."
        )

        # Generate and print a diff for immediate debugging
        diff = difflib.unified_diff(
            plain_content_normalized.splitlines(keepends=True),
            decoded_content_normalized.splitlines(keepends=True),
            fromfile="expected_plain_text",
            tofile="decoded_base64",
        )
        print("--- DIFF ---")
        sys.stdout.writelines(diff)
        print("--- END DIFF ---")

        sys.exit(1)


if __name__ == "__main__":
    # Assuming the main output files from the reporter script
    plain_file = "output/all.txt"
    base64_file = "output/base64_all.txt"
    verify_subscription_files(plain_file, base64_file)
