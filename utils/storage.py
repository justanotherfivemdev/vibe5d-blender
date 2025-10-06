"""
Secure storage utility for Vibe4D addon.

Handles persistent storage of user credentials and custom instructions.
"""

import json 
import os 
import tempfile 
import shutil 
from pathlib import Path 
from typing import Dict ,Optional ,List 
import time 

from .logger import logger 


class SecureStorage :
    """Secure storage for user credentials and settings."""

    def __init__ (self ):

        self .config_dir =Path .home ()/".config"/"blender"/"vibe4d"
        self .credentials_file =self .config_dir /"credentials.json"
        self .instructions_file =self .config_dir /"instructions.json"
        self .settings_file =self .config_dir /"settings.json"


        self .config_dir .mkdir (parents =True ,exist_ok =True )

    def _atomic_write (self ,file_path :Path ,data :dict ,max_retries :int =3 )->bool :
        """
        Atomic write operation with retry logic.
        
        Args:
            file_path: Path to the target file
            data: Data to write
            max_retries: Maximum number of retry attempts
            
        Returns:
            bool: True if successful, False otherwise
        """
        for attempt in range (max_retries ):
            try :

                temp_file =None 
                with tempfile .NamedTemporaryFile (
                mode ='w',
                dir =file_path .parent ,
                prefix =f".{file_path.name}.",
                suffix =".tmp",
                delete =False 
                )as temp_file :

                    json .dump (data ,temp_file ,indent =2 ,ensure_ascii =False )
                    temp_file .flush ()
                    os .fsync (temp_file .fileno ())
                    temp_file_path =temp_file .name 


                os .chmod (temp_file_path ,0o600 )


                shutil .move (temp_file_path ,file_path )

                logger .debug (f"Successfully wrote {file_path} on attempt {attempt + 1}")
                return True 

            except Exception as e :
                logger .warning (f"Write attempt {attempt + 1} failed for {file_path}: {str(e)}")


                if temp_file and os .path .exists (temp_file .name ):
                    try :
                        os .unlink (temp_file .name )
                    except :
                        pass 

                if attempt <max_retries -1 :

                    time .sleep (0.1 *(2 **attempt ))
                else :
                    logger .error (f"Failed to write {file_path} after {max_retries} attempts")
                    return False 

        return False 

    def save_credentials (self ,user_id :str ,token :str ,email :str ="",plan :str ="")->bool :
        """Save user credentials securely."""
        try :
            credentials ={
            "user_id":user_id ,
            "token":token ,
            "email":email ,
            "plan":plan 
            }

            success =self ._atomic_write (self .credentials_file ,credentials )

            if success :
                pass 
            else :
                logger .error ("Failed to save credentials")

            return success 

        except Exception as e :
            logger .error (f"Failed to save credentials: {str(e)}")
            return False 

    def load_credentials (self )->Optional [Dict [str ,str ]]:
        """Load saved user credentials."""
        try :
            if not self .credentials_file .exists ():
                logger .debug ("No saved credentials found")
                return None 

            with open (self .credentials_file ,'r')as f :
                credentials =json .load (f )


            if not credentials .get ("user_id")or not credentials .get ("token"):
                logger .warning ("Invalid credentials file - missing required fields")
                return None 

            return credentials 

        except json .JSONDecodeError as e :
            logger .error (f"Invalid credentials file format: {str(e)}")
            return None 
        except Exception as e :
            logger .error (f"Failed to load credentials: {str(e)}")
            return None 

    def clear_credentials (self )->bool :
        """Clear saved user credentials."""
        try :
            if self .credentials_file .exists ():
                self .credentials_file .unlink ()

            return True 

        except Exception as e :
            logger .error (f"Failed to clear credentials: {str(e)}")
            return False 

    def save_custom_instructions (self ,instructions :List [Dict [str ,any ]])->bool :
        """
        Save custom instructions to persistent storage.
        
        Args:
            instructions: List of instruction dictionaries with 'text' and 'enabled' keys
            
        Returns:
            bool: True if successful, False otherwise
        """
        try :

            if not isinstance (instructions ,list ):
                logger .error (f"Invalid instructions format: expected list, got {type(instructions)}")
                return False 


            validated_instructions =[]
            for i ,instruction in enumerate (instructions ):
                if not isinstance (instruction ,dict ):
                    logger .error (f"Invalid instruction at index {i}: expected dict, got {type(instruction)}")
                    return False 

                if "text"not in instruction :
                    logger .error (f"Invalid instruction at index {i}: missing 'text' field")
                    return False 


                validated_instruction ={
                "text":str (instruction .get ("text","")),
                "enabled":bool (instruction .get ("enabled",True ))
                }
                validated_instructions .append (validated_instruction )


            success =self ._atomic_write (self .instructions_file ,validated_instructions )

            if success :
                logger .info (f"Saved {len(validated_instructions)} custom instructions")
            else :
                logger .error ("Failed to save custom instructions")

            return success 

        except Exception as e :
            logger .error (f"Failed to save custom instructions: {str(e)}")
            return False 

    def save_custom_instruction (self ,instruction_text :str )->bool :
        """
        Save single custom instruction to persistent storage.
        
        Args:
            instruction_text: Single instruction text string
            
        Returns:
            bool: True if successful, False otherwise
        """
        try :

            if not isinstance (instruction_text ,str ):
                logger .error (f"Invalid instruction format: expected str, got {type(instruction_text)}")
                return False 


            instruction_data ={
            "instruction":instruction_text .strip ()
            }


            success =self ._atomic_write (self .instructions_file ,instruction_data )

            if success :
                logger .info (f"Saved custom instruction ({len(instruction_text)} characters)")
            else :
                logger .error ("Failed to save custom instruction")

            return success 

        except Exception as e :
            logger .error (f"Failed to save custom instruction: {str(e)}")
            return False 

    def load_custom_instructions (self )->Optional [List [Dict [str ,any ]]]:
        """
        Load saved custom instructions.
        
        Returns:
            List of instruction dictionaries or None if no instructions found
        """
        try :
            if not self .instructions_file .exists ():
                logger .debug ("No saved custom instructions found")
                return None 

            with open (self .instructions_file ,'r')as f :
                data =json .load (f )


            if not isinstance (data ,list ):
                logger .error (f"Invalid instructions file format: expected list, got {type(data)}")
                return None 


            validated_instructions =[]
            for i ,instruction in enumerate (data ):
                if not isinstance (instruction ,dict ):
                    logger .warning (f"Invalid instruction at index {i}: expected dict, got {type(instruction)}")
                    continue 

                if "text"not in instruction :
                    logger .warning (f"Invalid instruction at index {i}: missing 'text' field")
                    continue 


                validated_instruction ={
                "text":str (instruction .get ("text","")),
                "enabled":bool (instruction .get ("enabled",True ))
                }
                validated_instructions .append (validated_instruction )

            logger .info (f"Loaded {len(validated_instructions)} custom instructions")
            return validated_instructions 

        except json .JSONDecodeError as e :
            logger .error (f"Invalid instructions file format: {str(e)}")
            return None 
        except Exception as e :
            logger .error (f"Failed to load custom instructions: {str(e)}")
            return None 

    def load_custom_instruction (self )->Optional [str ]:
        """
        Load saved single custom instruction.
        
        Returns:
            Instruction text string or None if no instruction found
        """
        try :
            if not self .instructions_file .exists ():
                return None 

            with open (self .instructions_file ,'r')as f :
                data =json .load (f )


            if isinstance (data ,list ):

                combined_instructions =[]
                for instruction in data :
                    if isinstance (instruction ,dict )and instruction .get ("enabled",True ):
                        text =instruction .get ("text","").strip ()
                        if text :
                            combined_instructions .append (text )

                if combined_instructions :

                    combined_text ="\n\n".join (combined_instructions )


                    self .save_custom_instruction (combined_text )

                    return combined_text 
                else :
                    return None 

            elif isinstance (data ,dict ):

                instruction_text =data .get ("instruction","")
                if instruction_text :
                    return instruction_text 
                else :
                    return None 
            else :
                logger .error (f"Invalid instruction file format: expected dict or list, got {type(data)}")
                return None 

        except json .JSONDecodeError as e :
            logger .error (f"Invalid instruction file format: {str(e)}")
            return None 
        except Exception as e :
            logger .error (f"Failed to load custom instruction: {str(e)}")
            return None 

    def clear_custom_instructions (self )->bool :
        """Clear saved custom instructions."""
        try :
            if self .instructions_file .exists ():
                self .instructions_file .unlink ()
                logger .info ("Custom instructions cleared")
            return True 

        except Exception as e :
            logger .error (f"Failed to clear custom instructions: {str(e)}")
            return False 

    def clear_custom_instruction (self )->bool :
        """Clear saved single custom instruction."""
        try :
            if self .instructions_file .exists ():
                self .instructions_file .unlink ()
                logger .info ("Custom instruction cleared")
            return True 

        except Exception as e :
            logger .error (f"Failed to clear custom instruction: {str(e)}")
            return False 

    def save_settings (self ,settings_data :Dict [str ,str ])->bool :
        """
        Save global settings.
        
        Args:
            settings_data: Dictionary containing settings data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try :

            if not isinstance (settings_data ,dict ):
                logger .error (f"Invalid settings format: expected dict, got {type(settings_data)}")
                return False 


            normalized_settings ={
            "agent_model":str (settings_data .get ("agent_model","gpt-5-mini")),
            "ask_model":str (settings_data .get ("ask_model","gpt-5-mini")),
            "model":str (settings_data .get ("model","gpt-5-mini")),
            "mode":str (settings_data .get ("mode","agent"))
            }


            success =self ._atomic_write (self .settings_file ,normalized_settings )

            if success :
                logger .info (f"Saved settings: agent_model={normalized_settings['agent_model']}, ask_model={normalized_settings['ask_model']}, mode={normalized_settings['mode']}")
            else :
                logger .error ("Failed to save settings")

            return success 

        except Exception as e :
            logger .error (f"Failed to save settings: {str(e)}")
            return False 

    def load_settings (self )->Optional [Dict [str ,str ]]:
        """
        Load saved global settings.
        
        Returns:
            Dictionary containing settings or None if no settings found
        """
        try :
            if not self .settings_file .exists ():
                logger .debug ("No saved settings found, using defaults")
                return None 

            with open (self .settings_file ,'r')as f :
                data =json .load (f )


            if not isinstance (data ,dict ):
                logger .error ("Invalid settings file format: expected dict")
                return None 


            settings ={
            "agent_model":str (data .get ("agent_model","gpt-5-mini")),
            "ask_model":str (data .get ("ask_model","gpt-5-mini")),
            "model":str (data .get ("model","gpt-5-mini")),
            "mode":str (data .get ("mode","agent"))
            }

            return settings 

        except json .JSONDecodeError as e :
            logger .error (f"Invalid settings file format: {str(e)}")
            return None 
        except Exception as e :
            logger .error (f"Failed to load settings: {str(e)}")
            return None 

    def clear_settings (self )->bool :
        """Clear saved global settings."""
        try :
            if self .settings_file .exists ():
                self .settings_file .unlink ()
                logger .info ("Global settings cleared")
            return True 

        except Exception as e :
            logger .error (f"Failed to clear settings: {str(e)}")
            return False 



secure_storage =SecureStorage ()