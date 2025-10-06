"""
Code Block component for displaying syntax-highlighted code with special UI.
Features header with language name, line numbers, and scrollable content.
"""

import blf 
import bpy 
import gpu 
from gpu_extras .batch import batch_for_shader 
import logging 
import time 
import math 
from typing import TYPE_CHECKING ,List ,Optional ,Callable 

from .base import UIComponent 
from .scrollview import ScrollView 
from ..theme import get_themed_style 
from ..styles import FontSizes ,MarkdownLayout 
from ..coordinates import CoordinateSystem 
from ..types import Bounds ,EventType ,UIEvent 

if TYPE_CHECKING :
    from ..renderer import UIRenderer 

logger =logging .getLogger (__name__ )


def get_code_block_max_height ():
    """Get maximum height for code blocks (scaled)."""
    return CoordinateSystem .scale_int (1800 )

def get_code_block_header_height ():
    """Get header height for code blocks (scaled)."""
    return CoordinateSystem .scale_int (32 )

def get_code_block_line_number_width ():
    """Get line number area width (scaled)."""
    return CoordinateSystem .scale_int (40 )

def get_code_block_padding ():
    """Get padding for code blocks (scaled)."""
    return CoordinateSystem .scale_int (8 )

def get_code_block_corner_radius ():
    """Get corner radius for code blocks (scaled)."""
    return CoordinateSystem .scale_int (6 )


class CodeBlockComponent (UIComponent ):
    """Component for displaying code blocks with special UI features."""

    def __init__ (self ,code :str ,language :str ="",x :int =0 ,y :int =0 ,width :int =600 ):

        self .code =code 
        self .language =language if language else "text"
        self .lines =code .split ('\n')if code else [""]

        logger .info (f"CodeBlock: Creating component - language='{self.language}', lines={len(self.lines)}, width={width}")


        self .corner_radius =get_code_block_corner_radius ()
        self .header_height =get_code_block_header_height ()
        self .line_number_width =get_code_block_line_number_width ()
        self .padding =get_code_block_padding ()
        self .max_height =get_code_block_max_height ()


        self .font_size =int (FontSizes .Default *MarkdownLayout .CODE_FONT_SIZE_MULTIPLIER )
        self .line_height =int (self .font_size *1.4 )


        initial_height =self ._calculate_required_height (code ,width )


        super ().__init__ (x ,y ,width ,initial_height )


        self .scroll_y =0 
        self .max_scroll_y =0 


        self .apply_themed_style ("code_block")


        self ._update_height ()


        self .add_event_handler (EventType .MOUSE_WHEEL ,self ._on_mouse_wheel )

        logger .info (f"CodeBlock: Component created - bounds={self.bounds}, max_scroll_y={self.max_scroll_y}")
        logger .debug (f"CodeBlockComponent created: {len(self.lines)} lines, language='{self.language}'")

    def apply_themed_style (self ,style_type :str ="code_block"):
        """Apply themed style to the code block component."""
        try :
            from ..colors import Colors 
            from ..theme import get_themed_style 


            self .style =get_themed_style ("panel")
            self .background_color =Colors .lighten_color (Colors .Panel ,-10 )
            self .header_background_color =Colors .lighten_color (Colors .Panel ,5 )
            self .border_color =Colors .Border 
            self .border_width =1 
            self .text_color =Colors .Text 
            self .line_number_color =Colors .TextMuted 
            self .language_color =Colors .Text 

        except Exception as e :
            logger .warning (f"Could not apply themed style: {e}")

            self .background_color =(0.08 ,0.08 ,0.08 ,1.0 )
            self .header_background_color =(0.12 ,0.12 ,0.12 ,1.0 )
            self .border_color =(0.24 ,0.24 ,0.24 ,1.0 )
            self .border_width =1 
            self .text_color =(0.9 ,0.9 ,0.9 ,1.0 )
            self .line_number_color =(0.6 ,0.6 ,0.6 ,1.0 )
            self .language_color =(0.9 ,0.9 ,0.9 ,1.0 )

    def _calculate_required_height (self ,code :str ,width :int )->int :
        """Calculate the required height for the code block."""
        lines =code .split ('\n')if code else [""]


        content_height =len (lines )*self .line_height +(self .padding *2 )


        total_height =content_height +self .header_height 


        max_allowed =self .max_height 

        return min (total_height ,max_allowed )

    def _update_height (self ):
        """Update component height based on content."""
        new_height =self ._calculate_required_height (self .code ,self .bounds .width )
        if new_height !=self .bounds .height :
            self .set_size (self .bounds .width ,new_height )

    def _on_mouse_wheel (self ,event :UIEvent )->bool :
        """Handle mouse wheel scrolling."""
        logger .info (f"CodeBlock: Mouse wheel event received - max_scroll_y={self.max_scroll_y}")

        if not self .bounds .contains_point (event .mouse_x ,event .mouse_y ):
            logger .info ("CodeBlock: Mouse wheel event outside bounds")
            return False 


        if self .max_scroll_y <=0 :
            logger .info ("CodeBlock: No scrolling needed - content fits")
            return False 


        wheel_delta =0 
        if 'wheel_direction'in event .data :

            wheel_delta =1 if event .data ['wheel_direction']=='DOWN'else -1 
            logger .info (f"CodeBlock: Wheel direction = {event.data['wheel_direction']}, delta = {wheel_delta}")
        elif 'wheel_delta'in event .data :

            wheel_delta =event .data ['wheel_delta']
            logger .info (f"CodeBlock: Wheel delta = {wheel_delta}")
        else :
            logger .info ("CodeBlock: No wheel data found in event")
            return False 

        scroll_speed =CoordinateSystem .scale_int (60 )


        old_scroll_y =self .scroll_y 
        self .scroll_y =max (0 ,min (self .scroll_y -wheel_delta *scroll_speed ,self .max_scroll_y ))

        logger .info (f"CodeBlock: Scroll position changed from {old_scroll_y} to {self.scroll_y}")


        return old_scroll_y !=self .scroll_y 

    def set_code (self ,code :str ,language :str =""):
        """Update the code content and language."""
        self .code =code 
        self .language =language if language else "text"
        self .lines =code .split ('\n')if code else [""]


        self ._update_height ()


        content_height =self .bounds .height -self .header_height 
        total_content_height =len (self .lines )*self .line_height +(self .padding *2 )
        self .max_scroll_y =max (0 ,total_content_height -content_height )


        self .scroll_y =max (0 ,min (self .scroll_y ,self .max_scroll_y ))

    def set_size (self ,width :int ,height :int ):
        """Override set_size to update scroll limits when size changes."""
        super ().set_size (width ,height )


        content_height =self .bounds .height -self .header_height 
        total_content_height =len (self .lines )*self .line_height +(self .padding *2 )
        self .max_scroll_y =max (0 ,total_content_height -content_height )


        self .scroll_y =max (0 ,min (self .scroll_y ,self .max_scroll_y ))

    def handle_event (self ,event )->bool :
        """Handle UI events."""

        if not self .bounds .contains_point (event .mouse_x ,event .mouse_y ):
            logger .info (f"CodeBlock: Event outside bounds - mouse({event.mouse_x}, {event.mouse_y}) not in {self.bounds}")
            return False 



        if hasattr (event ,'event_type')and event .event_type ==EventType .MOUSE_WHEEL :
            logger .info (f"CodeBlock: Handling mouse wheel event")
            if self ._on_mouse_wheel (event ):
                logger .info (f"CodeBlock: Mouse wheel handled")
                return True 


        logger .info (f"CodeBlock: Passing event to base component")
        return super ().handle_event (event )

    def render (self ,renderer :'UIRenderer'):
        """Render the code block component."""
        if not self .visible :
            return 


        renderer .draw_rounded_rect (self .bounds ,self .background_color ,self .corner_radius )


        if self .border_width >0 :
            renderer .draw_rounded_rect_outline (
            self .bounds ,
            self .border_color ,
            self .border_width ,
            self .corner_radius 
            )


        self ._render_header (renderer )


        self ._render_code_content (renderer )

    def _render_header (self ,renderer :'UIRenderer'):
        """Render the header with language name."""

        header_bounds =Bounds (
        self .bounds .x ,
        self .bounds .y +self .bounds .height -self .header_height ,
        self .bounds .width ,
        self .header_height 
        )


        renderer .draw_rounded_rect (header_bounds ,self .header_background_color ,self .corner_radius )


        border_bounds =Bounds (
        header_bounds .x ,
        header_bounds .y -1 ,
        header_bounds .width ,
        1 
        )
        renderer .draw_rect (border_bounds ,self .border_color )


        language_text =self .language .upper ()if self .language else "CODE"
        text_x =header_bounds .x +self .padding 
        text_y =header_bounds .y +(self .header_height -FontSizes .Default )//2 

        renderer .draw_text (
        language_text ,
        text_x ,
        text_y ,
        FontSizes .Default ,
        self .language_color ,
        0 
        )

    def _render_code_content (self ,renderer :'UIRenderer'):
        """Render the code content with line numbers and manual scrolling."""

        content_bounds =Bounds (
        self .bounds .x ,
        self .bounds .y ,
        self .bounds .width ,
        self .bounds .height -self .header_height 
        )


        renderer .push_clip_rect (content_bounds .x ,content_bounds .y ,content_bounds .width ,content_bounds .height )

        try :

            first_visible_line =max (0 ,int (self .scroll_y //self .line_height ))
            last_visible_line =min (
            len (self .lines ),
            int ((self .scroll_y +content_bounds .height )//self .line_height )+2 
            )


            line_num_bg_bounds =Bounds (
            content_bounds .x ,
            content_bounds .y ,
            self .line_number_width ,
            content_bounds .height 
            )
            renderer .draw_rect (line_num_bg_bounds ,self .background_color )


            separator_bounds =Bounds (
            content_bounds .x +self .line_number_width ,
            content_bounds .y ,
            1 ,
            content_bounds .height 
            )
            renderer .draw_rect (separator_bounds ,self .border_color )


            for line_idx in range (first_visible_line ,last_visible_line ):
                if line_idx >=len (self .lines ):
                    break 

                line_text =self .lines [line_idx ]
                line_number =line_idx +1 



                line_y_from_top =(line_idx *self .line_height )+self .padding -self .scroll_y 
                line_y =content_bounds .y +content_bounds .height -line_y_from_top -self .line_height 


                if line_y +self .line_height <content_bounds .y or line_y >content_bounds .y +content_bounds .height :
                    continue 


                line_num_text =str (line_number ).rjust (3 )
                line_num_x =content_bounds .x +self .padding 

                try :
                    renderer .draw_text (
                    line_num_text ,
                    line_num_x ,
                    line_y ,
                    self .font_size ,
                    self .line_number_color ,
                    0 
                    )
                except Exception as e :
                    logger .warning (f"Error rendering line number {line_number}: {e}")


                code_x =content_bounds .x +self .line_number_width +self .padding 

                try :
                    renderer .draw_text (
                    line_text ,
                    code_x ,
                    line_y ,
                    self .font_size ,
                    self .text_color ,
                    0 
                    )
                except Exception as e :
                    logger .warning (f"Error rendering code line {line_number}: {e}")


            if self .max_scroll_y >0 :
                self ._render_scrollbar (renderer ,content_bounds )

        except Exception as e :
            logger .error (f"Error in _render_code_content: {e}")
        finally :
            renderer .pop_clip_rect ()

    def _render_scrollbar (self ,renderer :'UIRenderer',content_bounds :Bounds ):
        """Render a simple scrollbar."""
        scrollbar_width =CoordinateSystem .scale_int (8 )


        scrollbar_bounds =Bounds (
        content_bounds .x +content_bounds .width -scrollbar_width ,
        content_bounds .y ,
        scrollbar_width ,
        content_bounds .height 
        )


        scrollbar_bg_color =(0.2 ,0.2 ,0.2 ,0.8 )
        renderer .draw_rect (scrollbar_bounds ,scrollbar_bg_color )


        total_content_height =len (self .lines )*self .line_height +(self .padding *2 )
        thumb_height =max (20 ,int (content_bounds .height *(content_bounds .height /total_content_height )))


        scroll_ratio =self .scroll_y /self .max_scroll_y if self .max_scroll_y >0 else 0 
        thumb_y =scrollbar_bounds .y +int ((scrollbar_bounds .height -thumb_height )*scroll_ratio )


        thumb_bounds =Bounds (
        scrollbar_bounds .x ,
        thumb_y ,
        scrollbar_width ,
        thumb_height 
        )

        thumb_color =(0.6 ,0.6 ,0.6 ,0.9 )
        renderer .draw_rect (thumb_bounds ,thumb_color )

    def cleanup (self ):
        """Clean up resources."""
        super ().cleanup ()