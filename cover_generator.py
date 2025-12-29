from PIL import Image, ImageDraw, ImageFont
import io
import os
from typing import Tuple
from llm_client import llm, GHOSTWRITER_FICTION
from config import settings

class CoverGenerator:
    """Generate book covers for eBook and print"""
    
    # Standard dimensions
    EBOOK_SIZE = (1600, 2560)  # Amazon KDP recommended
    PRINT_6x9_SIZE = (1875, 2850)  # 6x9 inch at 300 DPI
    PRINT_5x8_SIZE = (1563, 2500)  # 5x8 inch at 300 DPI
    
    def __init__(self):
        self.output_dir = "covers"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_cover_concept(self, title: str, genre: str, themes: list) -> dict:
        """Use LLM to generate cover design concept"""
        prompt = f"""Design a book cover concept for:

Title: {title}
Genre: {genre}
Themes: {', '.join(themes) if themes else 'mystery, suspense'}

Provide a JSON response with:
{{
  "color_scheme": ["primary_color", "secondary_color", "accent_color"],
  "imagery": "description of visual elements",
  "mood": "overall atmosphere",
  "typography_style": "font mood (e.g., gothic, modern, elegant)",
  "layout": "composition description"
}}
"""
        
        try:
            response = llm.generate(prompt, GHOSTWRITER_FICTION, settings.structured_model)
            import json
            return json.loads(response)
        except:
            # Fallback to default dark/mysterious theme
            return {
                "color_scheme": ["#0a0a0a", "#8b0000", "#ffd700"],
                "imagery": "Dark, mysterious atmosphere",
                "mood": "suspenseful",
                "typography_style": "gothic",
                "layout": "centered title with dramatic background"
            }
    
    def create_ebook_cover(self, title: str, author: str, genre: str = "Fiction", themes: list = None) -> str:
        """Generate eBook cover (1600x2560)"""
        concept = self.generate_cover_concept(title, genre, themes or [])
        
        # Create image
        img = Image.new('RGB', self.EBOOK_SIZE, color=concept['color_scheme'][0])
        draw = ImageDraw.Draw(img)
        
        # Add gradient background
        self._add_gradient(img, concept['color_scheme'])
        
        # Add title
        self._add_text(
            draw, 
            title, 
            position=(self.EBOOK_SIZE[0] // 2, self.EBOOK_SIZE[1] // 3),
            font_size=120,
            color=concept['color_scheme'][2],
            max_width=self.EBOOK_SIZE[0] - 200
        )
        
        # Add author
        self._add_text(
            draw,
            f"by {author}",
            position=(self.EBOOK_SIZE[0] // 2, self.EBOOK_SIZE[1] * 2 // 3),
            font_size=60,
            color="#ffffff",
            max_width=self.EBOOK_SIZE[0] - 200
        )
        
        # Add genre label
        self._add_text(
            draw,
            genre.upper(),
            position=(self.EBOOK_SIZE[0] // 2, self.EBOOK_SIZE[1] - 200),
            font_size=40,
            color=concept['color_scheme'][1],
            max_width=self.EBOOK_SIZE[0] - 200
        )
        
        # Save
        filename = f"{self.output_dir}/ebook_{title[:30].replace(' ', '_')}.png"
        img.save(filename, 'PNG', quality=95)
        return filename
    
    def create_print_cover(self, title: str, author: str, page_count: int, size: str = "6x9", genre: str = "Fiction", themes: list = None) -> str:
        """Generate print cover with spine (full wrap)"""
        concept = self.generate_cover_concept(title, genre, themes or [])
        
        # Calculate spine width (approximate: 0.002252 inches per page)
        spine_width_inches = page_count * 0.002252
        spine_width_px = int(spine_width_inches * 300)  # Convert to pixels at 300 DPI
        
        # Dimensions
        if size == "6x9":
            cover_width, cover_height = self.PRINT_6x9_SIZE
        else:
            cover_width, cover_height = self.PRINT_5x8_SIZE
        
        # Total width = front + spine + back
        total_width = (cover_width * 2) + spine_width_px
        
        # Create full wrap image
        img = Image.new('RGB', (total_width, cover_height), color=concept['color_scheme'][0])
        draw = ImageDraw.Draw(img)
        
        # Add gradient
        self._add_gradient(img, concept['color_scheme'])
        
        # FRONT COVER (right side)
        front_x_center = cover_width + spine_width_px + (cover_width // 2)
        
        self._add_text(
            draw,
            title,
            position=(front_x_center, cover_height // 3),
            font_size=100,
            color=concept['color_scheme'][2],
            max_width=cover_width - 200
        )
        
        self._add_text(
            draw,
            f"by {author}",
            position=(front_x_center, cover_height * 2 // 3),
            font_size=50,
            color="#ffffff",
            max_width=cover_width - 200
        )
        
        # SPINE
        spine_x_center = cover_width + (spine_width_px // 2)
        self._add_vertical_text(
            draw,
            f"{title} - {author}",
            position=(spine_x_center, cover_height // 2),
            font_size=40,
            color="#ffffff"
        )
        
        # BACK COVER (left side)
        back_x_center = cover_width // 2
        self._add_text(
            draw,
            "[Barcode Here]",
            position=(back_x_center, cover_height - 400),
            font_size=30,
            color="#ffffff",
            max_width=cover_width - 200
        )
        
        # Save
        filename = f"{self.output_dir}/print_{title[:30].replace(' ', '_')}.png"
        img.save(filename, 'PNG', quality=95, dpi=(300, 300))
        return filename
    
    def _add_gradient(self, img: Image, colors: list):
        """Add gradient background"""
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        # Simple top-to-bottom gradient
        for y in range(height):
            alpha = y / height
            draw.line(
                [(0, y), (width, y)],
                fill=self._interpolate_color(colors[0], colors[1], alpha)
            )
    
    def _interpolate_color(self, color1: str, color2: str, alpha: float) -> str:
        """Interpolate between two hex colors"""
        c1 = tuple(int(color1.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        c2 = tuple(int(color2.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        result = tuple(int(c1[i] + (c2[i] - c1[i]) * alpha) for i in range(3))
        return f"#{result[0]:02x}{result[1]:02x}{result[2]:02x}"
    
    def _add_text(self, draw: ImageDraw, text: str, position: Tuple[int, int], font_size: int, color: str, max_width: int):
        """Add centered text to image"""
        try:
            # Try to use a nice font, fallback to default
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Word wrap if needed
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw lines
        y_offset = position[1] - (len(lines) * font_size // 2)
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = position[0] - (text_width // 2)
            y = y_offset + (i * font_size * 1.2)
            draw.text((x, y), line, font=font, fill=color)
    
    def _add_vertical_text(self, draw: ImageDraw, text: str, position: Tuple[int, int], font_size: int, color: str):
        """Add vertical text for spine"""
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Create temporary image for rotation
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        txt_img = Image.new('RGBA', (text_width, text_height), (255, 255, 255, 0))
        txt_draw = ImageDraw.Draw(txt_img)
        txt_draw.text((0, 0), text, font=font, fill=color)
        
        # Rotate and paste
        rotated = txt_img.rotate(90, expand=True)
        # Note: This is simplified - full implementation would paste the rotated text


cover_gen = CoverGenerator()
