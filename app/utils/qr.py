from io import BytesIO

import qrcode
import qrcode.image.svg


def patient_qr_svg(patient_id: str) -> str:
    image = qrcode.make(patient_id, image_factory=qrcode.image.svg.SvgPathImage, box_size=6, border=2)
    output = BytesIO()
    image.save(output)
    return output.getvalue().decode("utf-8")
