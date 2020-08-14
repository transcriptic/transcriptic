from io import BytesIO

from transcriptic import api

try:
    from PIL import Image
except ImportError:
    raise ImportError(
        "Please run `pip install transcriptic[analysis] if you "
        "would like to use the Transcriptic analysis module."
    )


class ImagePlate(object):
    """
    An ImagePlate object generalizes the parsing of datasets derived from the
    plate camera for easy visualization.

    Parameters
    ----------
    dataset: dataset
        Single dataset selected from datasets object

    Attributes
    ----------
    raw: BytesIO
        Raw buffer of image bytes
    image: PIL.Image
        Image object as rendered by PIL
    """

    def __init__(self, dataset):
        if dataset.attributes["instruction"]["operation"]["op"] != "image_plate":
            raise RuntimeError("No image_plate operation found for given dataset.")
        self.id = dataset.id
        self.raw = BytesIO()
        req = api.raw_image_data(data_id=self.id)
        # Buffer download of data
        chunk_sz = 512
        for chunk in req.iter_content(chunk_sz):
            self.raw.write(chunk)
        # Reset seek to 0
        self.raw.seek(0)
        self.image = Image.open(self.raw)

    def display(self):
        """
        Displays the original full-sized image. Helpful when used in an IPython
        kernel

        Returns
        -------
        HTML
            Returns a HTML iframe of the full-size image which is rendered nicely in IPython (if IPython is present)
        """
        try:
            # pylint: disable=import-error
            from IPython.display import HTML

            return HTML(
                """<iframe src="%s")" frameborder="0" \
                allowtransparency="true" style="height:500px;" seamless> \
                </iframe>"""
                % api.get_route("view_raw_image", data_id=self.id)
            )

        except:
            # If IPython module is not present or unable to show, display using
            # default PIL image show
            self.image.show()
