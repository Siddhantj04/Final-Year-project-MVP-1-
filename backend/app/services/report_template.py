DISCLAIMER = (
    "DISCLAIMER: This output is generated for education and workflow support only. "
    "It is not a clinical diagnosis and must be reviewed by a qualified radiologist "
    "before any educational or research use."
)

HEATMAP_NOTICE = (
    "The Grad-CAM heatmap is an explanation aid highlighting regions that influenced "
    "the model output; it is not a clinical finding."
)


def build_template_report(
    predicted_class: str,
    confidence: float,
    quality_status: str,
    quality_messages: list[str],
) -> str:
    class_label = "Normal-like chest X-ray pattern" if predicted_class == "normal_like" else "Possible pneumonia-like pattern"
    quality_lines = "\n".join(f"- {m}" for m in quality_messages) if quality_messages else "- No quality messages recorded."

    return f"""RadiologyLearn AI — Structured Preliminary Report (Template)

{DISCLAIMER}

Study type: Chest radiograph (uploaded image)
Image quality status: {quality_status}
Quality assessment notes:
{quality_lines}

AI model output (binary classifier):
- Predicted category: {class_label}
- Confidence score: {confidence:.2%}
- Model classes: normal_like vs pneumonia_like (educational labels only)

Explainability:
- {HEATMAP_NOTICE}

Reviewer action required:
- A qualified reviewer must approve, edit, reject, or mark unsuitable before this case is considered complete.

End of template report.
"""
