from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import os
import requests
from typing import Tuple, List
from llm_client import llm, GHOSTWRITER_FICTION
from config import settings

class CoverGenerator:
    """Generate book covers - both free basic and premium AI-generated"""
    
    # Standard dimensions
    EBOOK_SIZE = (1600, 2560)  # Amazon KDP recommended
    PRINT_6x9_SIZE = (1875, 2850)  # 6x9 inch at 300 DPI
    PRINT_5x8_SIZE = (1563, 2500)  # 5x8 inch at 300 DPI
    
    def __init__(self):
        self.output_dir = "covers"
        os.makedirs(self.output_dir, exist_ok=True)
        self.xai_api_key = settings.xai_api_key
    
    # ==================== FREE BASIC COVERS ====================
    
    def create_basic_cover(self, title: str, author: str, genre: str = "Fiction", 
                          style: str = "dark", size: Tuple[int, int] = None) -> str:
        """Create FREE basic cover with enhanced PIL design (no AI cost)"""
        size = size or self.EBOOK_SIZE
        
        # Genre-based color schemes
        color_schemes = {
            "dark": {
                "bg_start": "#0a0a0a",
                "bg_end": "#1a1a2e",
                "title": "#00fff9",
                "author": "#ffffff",
                "accent": "#ff006e"
            },
            "mystery": {
                "bg_start": "#1a0000",
                "bg_end": "#4a0000",
                "title": "#ffd700",
                "author": "#cccccc",
                "accent": "#8b0000"
            },
            "fantasy": {
                "bg_start": "#1a004a",
                "bg_end": "#4a1a7a",
                "title": "#7a27ff",
                "author": "#ffffff",
                "accent": "#39FF14"
            },
            "romance": {
                "bg_start": "#4a001a",
                "bg_end": "#7a1a4a",
                "title": "#ff69b4",
                "author": "#ffffff",
                "accent": "#ffd700"
            },
            "scifi": {
                "bg_start": "#001a1a",
                "bg_end": "#004a4a",
                "title": "#00ffff",
                "author": "#ffffff",
                "accent": "#00ff00"
            }
        }
        
        # Select color scheme
        if genre.lower() in color_schemes:
            colors = color_schemes[genre.lower()]
        else:
            colors = color_schemes[style]
        
        # Create base image
        img = Image.new('RGB', size, color=colors['bg_start'])
        draw = ImageDraw.Draw(img)
        
        # Add gradient background
        self._add_smooth_gradient(img, colors['bg_start'], colors['bg_end'])
        
        # Add texture/noise for depth
        self._add_texture(img)
        
        # Add geometric shapes for visual interest
        self._add_geometric_accents(draw, size, colors['accent'])
        
        # Add border frame
        self._add_border(draw, size, colors['accent'])
        
        # Add title with shadow effect
        self._add_text_with_shadow(
            draw, 
            title, 
            position=(size[0] // 2, size[1] // 3),
            font_size=min(120, size[0] // 10),
            color=colors['title'],
            shadow_color=colors['accent'],
            max_width=size[0] - 200,
            bold=True
        )
        
        # Add author with glow effect
        self._add_text_with_shadow(
            draw,
            f"by {author}",
            position=(size[0] // 2, size[1] * 2 // 3),
            font_size=min(60, size[0] // 20),
            color=colors['author'],
            shadow_color=colors['accent'],
            max_width=size[0] - 200,
            bold=False
        )
        
        # Add genre badge
        self._add_badge(draw, genre.upper(), size, colors['accent'])
        
        # Enhance image (sharpen, adjust contrast)
        img = img.filter(ImageFilter.SHARPEN)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
        
        # Save
        filename = f"{self.output_dir}/basic_{title[:30].replace(' ', '_')}.png"
        img.save(filename, 'PNG', quality=95)
        return filename
    
    def _add_smooth_gradient(self, img: Image, color1: str, color2: str):
        """Add smooth gradient background"""
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        c1 = self._hex_to_rgb(color1)
        c2 = self._hex_to_rgb(color2)
        
        for y in range(height):
            alpha = y / height
            r = int(c1[0] + (c2[0] - c1[0]) * alpha)
            g = int(c1[1] + (c2[1] - c1[1]) * alpha)
            b = int(c1[2] + (c2[2] - c1[2]) * alpha)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    def _add_texture(self, img: Image):
        """Add subtle noise texture for depth"""
        import random
        pixels = img.load()
        width, height = img.size
        
        for x in range(0, width, 3):
            for y in range(0, height, 3):
                if random.random() < 0.1:  # 10% of pixels
                    noise = random.randint(-15, 15)
                    r, g, b = pixels[x, y]
                    pixels[x, y] = (
                        max(0, min(255, r + noise)),
                        max(0, min(255, g + noise)),
                        max(0, min(255, b + noise))
                    )
    
    def _add_geometric_accents(self, draw: ImageDraw, size: Tuple[int, int], color: str):
        """Add geometric shapes for visual interest"""
        width, height = size
        
        # Diagonal lines in corners
        for i in range(5):
            offset = i * 20
            # Top left
            draw.line([(0, offset), (offset, 0)], fill=color, width=2)
            # Bottom right
            draw.line([(width - offset, height), (width, height - offset)], fill=color, width=2)
    
    def _add_border(self, draw: ImageDraw, size: Tuple[int, int], color: str):
        """Add decorative border"""
        width, height = size
        margin = 30
        
        # Outer border
        draw.rectangle(
            [(margin, margin), (width - margin, height - margin)],
            outline=color,
            width=3
        )
        
        # Inner border (thinner)
        inner_margin = margin + 10
        draw.rectangle(
            [(inner_margin, inner_margin), (width - inner_margin, height - inner_margin)],
            outline=color,
            width=1
        )
    
    def _add_badge(self, draw: ImageDraw, text: str, size: Tuple[int, int], color: str):
        """Add genre badge at bottom"""
        width, height = size
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Badge background
        badge_x = (width - text_width) // 2 - 20
        badge_y = height - 200
        badge_width = text_width + 40
        badge_height = text_height + 20
        
        draw.rectangle(
            [(badge_x, badge_y), (badge_x + badge_width, badge_y + badge_height)],
            fill=self._hex_to_rgb(color) + (100,),
            outline=color,
            width=2
        )
        
        # Badge text
        text_x = (width - text_width) // 2
        text_y = badge_y + 10
        draw.text((text_x, text_y), text, font=font, fill="#ffffff")
    
    def _add_text_with_shadow(self, draw: ImageDraw, text: str, position: Tuple[int, int], 
                              font_size: int, color: str, shadow_color: str, 
                              max_width: int, bold: bool = True):
        """Add text with drop shadow effect"""
        try:
            font_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
            font = ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{font_name}", font_size)
        except:
            font = ImageFont.load_default()
        
        # Word wrap
        lines = self._wrap_text(draw, text, font, max_width)
        
        # Calculate total text height
        total_height = len(lines) * font_size * 1.2
        y_offset = position[1] - (total_height // 2)
        
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = position[0] - (text_width // 2)
            y = y_offset + (i * font_size * 1.2)
            
            # Draw shadow (offset)
            shadow_offset = 5
            draw.text(
                (x + shadow_offset, y + shadow_offset), 
                line, 
                font=font, 
                fill=self._hex_to_rgb(shadow_color)
            )
            
            # Draw main text
            draw.text((x, y), line, font=font, fill=self._hex_to_rgb(color))
    
    def _wrap_text(self, draw: ImageDraw, text: str, font: ImageFont, max_width: int) -> List[str]:
        """Wrap text to fit within max width"""
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
        
        return lines
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    # ==================== PREMIUM AI-GENERATED COVERS ====================
    
    def generate_ai_cover_options(self, title: str, author: str, genre: str = "Fiction", 
                                 themes: list = None, style_preference: str = None) -> List[dict]:
        """Generate 4 AI cover options using Grok image generation (costs credits)"""
        
        # Generate diverse prompts for variety
        prompts = self._create_cover_prompts(title, genre, themes, style_preference)
        
        cover_options = []
        
        for i, prompt in enumerate(prompts[:4]):  # Generate 4 options
            try:
                # Call xAI Grok image generation API
                image_url = self._generate_grok_image(prompt)
                
                if image_url:
                    # Download and save image
                    filename = f"{self.output_dir}/ai_{title[:20].replace(' ', '_')}_option{i+1}.jpg"
                    self._download_image(image_url, filename)
                    
                    cover_options.append({
                        "option_number": i + 1,
                        "prompt": prompt,
                        "image_path": filename,
                        "image_url": image_url
                    })
            except Exception as e:
                print(f"Failed to generate cover option {i+1}: {e}")
                continue
        
        return cover_options
    
    def _create_cover_prompts(self, title: str, genre: str, themes: list = None, 
                             style_preference: str = None) -> List[str]:
        """Create 4 diverse cover design prompts"""
        base_themes = ', '.join(themes) if themes else 'mystery and intrigue'
        
        # Use LLM to generate creative prompts
        llm_prompt = f"""Generate 4 diverse book cover design prompts for:

Title: {title}
Genre: {genre}
Themes: {base_themes}
{f'Style preference: {style_preference}' if style_preference else ''}

Create 4 different visual approaches:
1. Photorealistic/cinematic
2. Artistic/illustrated 
3. Minimalist/symbolic
4. Dramatic/atmospheric

Each prompt should be detailed, specify composition, lighting, colors, and mood.
Return as JSON array of 4 strings."""
        
        try:
            response = llm.generate(llm_prompt, GHOSTWRITER_FICTION, settings.structured_model)
            import json
            prompts = json.loads(response)
            
            # Add text overlay instruction to each
            enhanced_prompts = [
                f"{p} Professional book cover design with title '{title}' prominently displayed in elegant typography. High quality, print-ready, 1600x2560px portrait orientation."
                for p in prompts
            ]
            return enhanced_prompts
        except:
            # Fallback manual prompts
            return [
                f"Cinematic photorealistic book cover for '{title}', {genre} novel, {base_themes}, dramatic lighting, moody atmosphere, title in bold elegant font",
                f"Artistic illustrated book cover for '{title}', {genre} style, {base_themes}, painterly aesthetic, rich colors, stylized typography",
                f"Minimalist symbolic book cover for '{title}', {genre}, {base_themes}, clean design, strong visual metaphor, modern typography",
                f"Dark atmospheric book cover for '{title}', {genre} novel, {base_themes}, mysterious mood, cinematic composition, striking title treatment"
            ]
    
    def _generate_grok_image(self, prompt: str) -> str:
        """Call xAI Grok API to generate image"""
        url = "https://api.x.ai/v1/images/generations"
        
        headers = {
            "Authorization": f"Bearer {self.xai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "grok-2-image-1212",
            "prompt": prompt,
            "n": 1,  # Generate 1 image per call
            "size": "1600x2560",  # eBook cover size
            "response_format": "url"
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data['data'][0]['url']
    
    def _download_image(self, url: str, filename: str):
        """Download image from URL and save locally"""
        response = requests.get(url)
        response.raise_for_status()
        
        with open(filename, 'wb') as f:
            f.write(response.content)
    
    # ==================== PRINT COVERS ====================
    
    def create_print_cover(self, title: str, author: str, page_count: int, 
                          size: str = "6x9", genre: str = "Fiction", 
                          front_cover_path: str = None) -> str:
        """Generate print cover with spine (uses existing front cover)"""
        
        # Calculate spine width
        spine_width_inches = page_count * 0.002252
        spine_width_px = int(spine_width_inches * 300)
        
        # Dimensions
        if size == "6x9":
            cover_width, cover_height = self.PRINT_6x9_SIZE
        else:
            cover_width, cover_height = self.PRINT_5x8_SIZE
        
        total_width = (cover_width * 2) + spine_width_px
        
        # Create base
        img = Image.new('RGB', (total_width, cover_height), color='#0a0a0a')
        
        # If front cover provided, paste it
        if front_cover_path and os.path.exists(front_cover_path):
            front_img = Image.open(front_cover_path)
            front_img = front_img.resize((cover_width, cover_height))
            img.paste(front_img, (cover_width + spine_width_px, 0))
        else:
            # Generate basic front cover
            front_cover = self.create_basic_cover(title, author, genre, size=(cover_width, cover_height))
            front_img = Image.open(front_cover)
            img.paste(front_img, (cover_width + spine_width_px, 0))
        
        # Add spine and back
        draw = ImageDraw.Draw(img)
        
        # Spine text (vertical)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        spine_text = f"{title} - {author}"
        # Note: Proper vertical text rotation would require additional PIL operations
        
        # Back cover - simple design
        back_x_center = cover_width // 2
        draw.text((back_x_center - 100, cover_height - 400), "[Barcode Area]", font=font, fill="#ffffff")
        
        filename = f"{self.output_dir}/print_{title[:30].replace(' ', '_')}.png"
        img.save(filename, 'PNG', quality=95, dpi=(300, 300))
        return filename


cover_gen = CoverGenerator()
