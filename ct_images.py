"""
    Images processing module
"""
import ct_files
from ct_palette import palette
from ct_palette import density_list
from PIL import Image, ImageDraw, ImageFont

TILE_HEIGHT = 16
TILE_WIDTH = 16
FONT_SIZE = 20


def calculate_new_size(size, file_dict):
    """
        Downscaling the file
    """
    scale = file_dict.get('scale', 6)
    input_width, input_height = size
    output_height = input_height // scale
    output_width = input_width // scale
    return output_width, output_height


def make_image(source_image, file_dict):
    """
        Main computation cycle
    """
    width, height = calculate_new_size(source_image.size, file_dict)
    source_image = source_image.resize((width, height), 0)
    source_image = source_image.convert(mode='RGB')

    output_height = height * TILE_HEIGHT
    output_width = width * TILE_WIDTH
    output_image = Image.new(mode='RGB', size=(output_width, output_height), color=(0, 0, 0))

    font = ImageFont.truetype('Anonymous.ttf', FONT_SIZE)

    position = 0

    for y in range(height):
        for x in range(width):
            """ Creating new symbolic tile  """
            rgb_color = source_image.getpixel((x, y))
            density = density_list[sum(rgb_color)]

            text_tile = Image.new(mode="RGB", size=(TILE_WIDTH, TILE_HEIGHT), color=(0, 0, 0))
            textdraw = ImageDraw.ImageDraw(text_tile, "RGB")
            textdraw.text((2, 0), text=palette[density], font=font, fill=rgb_color)

            output_image.paste(text_tile, (x * TILE_WIDTH, y * TILE_HEIGHT))

            position += 1

    return output_image


def analyse_image(image):
    """
        Pre-process pass over the image to determine the mode (full or additive).
        Need to know the mode before processing all frames.
    """
    results = {'size': image.size, 'mode': 'full'}
    try:
        while True:
            if image.tile:
                tile = image.tile[0]
                update_region = tile[1]
                update_region_dimensions = update_region[2:]
                if update_region_dimensions != image.size:
                    results['mode'] = 'partial'
                    break
            image.seek(image.tell() + 1)
    except EOFError:
        pass
    return results


def make_frames(source_image, file_dict):
    """
        Extract frames from GIF
    """
    mode = analyse_image(source_image)['mode']
    gif_palette = source_image.getpalette()
    last_frame = None
    total_frames = source_image.n_frames

    frames = []

    for x in range(total_frames + 1):
        print(f'\rFrame: {str(x)} of {str(source_image.n_frames)}', end='')
        try:
            if not source_image.getpalette():
                source_image.putpalette(gif_palette)

            source_image.seek(x)
            empty_frame = Image.new('RGB', source_image.size)

            if mode == 'partial' and last_frame:
                empty_frame.paste(last_frame, (0, 0))

            empty_frame.paste(source_image, (0, 0))
            new_frame = make_image(source_image=empty_frame, file_dict=file_dict)
            last_frame = new_frame
            frames.append(new_frame)
        except EOFError:
            break
    print()
    return frames


def convert(file_dict):
    """
        Load file for the image
    """
    status = 0

    with open(file_dict['path'], mode='rb') as file:
        image = Image.open(file)

        if file_dict.get('ext') == 'gif':
            frames = make_frames(source_image=image, file_dict=file_dict)
            status = ct_files.save_gif(file_dict, frames)

        elif file_dict.get('ext') in ['bmp', 'jpg', 'png']:
            converted_image = make_image(source_image=image, file_dict=file_dict)
            status = ct_files.save_image(file_dict, converted_image)

    ct_files.move_file(file_dict)
    return status

