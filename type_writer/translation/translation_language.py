import pypinyin
import sys
from pypinyin import pinyin, Style
import re
from config.loader import get_config

class ChineseToBraille:
    def __init__(self):
        self.initials_braille = {

            'b':    [1,1,0,0,0,0],
            'p':    [1,1,1,1,0,0],
            'm':    [1,0,1,1,0,0],
            'f':    [1,1,0,1,0,0],
            'd':    [1,0,0,1,1,0],
            't':    [0,1,1,1,1,0],
            'n':    [1,0,1,1,1,0],
            'l':    [1,1,1,0,0,0],
            'g':    [1,1,0,1,1,0],
            'k':    [1,0,1,0,0,0],
            'h':    [1,1,0,0,1,0],
            'j':    [1,1,0,1,1,0],
            'q':    [1,0,1,0,0,0],
            'x':    [1,1,0,0,1,0],
            'zh':   [0,0,1,1,0,0],
            'ch':   [1,1,1,1,1,0],
            'sh':   [1,0,0,0,1,1],
            'r':    [0,1,0,1,1,0],
            'z':    [1,0,1,0,1,1],
            'c':    [1,0,0,1,0,0],
            's':    [0,1,1,1,0,0],
            'y':    [0,0,0,0,0,0],
            'w':    [0,0,0,0,0,0],
        }

        self.finals_braille = {

            'a':    [0,0,1,0,1,0],
            'o':    [0,1,0,0,0,1],
            'e':    [0,1,0,0,0,1],
            'i':    [0,1,0,1,0,0],
            'u':    [1,0,1,0,0,1],
            'v':    [0,0,1,1,0,1],
            'ü':    [0,0,1,1,0,1],
            'ai':   [0,1,0,1,0,1],
            'ei':   [0,1,1,1,0,1],
            'ao':   [0,1,1,0,1,0],
            'ou':   [1,1,1,0,1,1],
            'an':   [1,1,1,0,0,1],
            'en':   [0,0,1,0,1,1],
            'ang':  [0,1,1,0,0,1],
            'eng':  [0,0,1,1,1,1],
            'ong':  [0,1,0,0,1,1],
            'er':   [1,1,1,0,1,0],
            'ia':   [1,1,0,1,0,1],
            'ie':   [1,0,0,0,1,0],
            'iao':  [0,0,1,1,1,0],
            'iu':   [1,1,0,0,1,1],
            'ian':  [1,0,0,1,0,1],
            'in':   [1,1,0,0,0,1],
            'iang': [1,0,1,1,0,1],
            'ing':  [1,0,0,0,0,1],
            'iong': [1,0,0,1,1,1],
            'ua':   [1,1,1,1,1,1],
            'uo':   [1,0,1,0,1,0],
            'uai':  [1,0,1,1,1,1],
            'uei':  [0,1,0,1,1,1],
            'ui':   [0,1,0,1,1,1],
            'uan':  [1,1,0,1,1,1],
            'un':   [0,0,0,1,1,1],
            'uang': [0,1,1,0,1,1],
            'ueng': [0,1,0,0,1,1],
            've':   [0,1,1,1,1,1],
            'vn':   [0,0,0,1,1,1],
        }

        self.tones_braille = {
            '1':    [1,0,0,0,0,0],
            '2':    [0,1,0,0,0,0],
            '3':    [0,0,1,0,0,0],
            '4':    [0,1,1,0,0,0],
            '5':    [0,0,0,0,0,0],
        }

        cfg = get_config()
        self._flip_dots_enabled = cfg.get("translation", {}).get("flip_dots", False)
    
    def load_standard_mapping(self, mapping_file):
        pass

    def chinese_to_pinyin(self, text: str) -> list:
        pinyin_list = pinyin(text, style=Style.TONE3, heteronym=False, errors='ignore')
        return [item[0] for item in pinyin_list]

    def parse_pinyin(self, pinyin_str: str):
        tone_match = re.search(r'(\d)$', pinyin_str)
        tone = tone_match.group(1) if tone_match else '1'
        pinyin_no_tone = pinyin_str.rstrip('12345')

        special_map = {
            'zi': ('z', 'i'), 'ci': ('c', 'i'), 'si': ('s', 'i'),
            'zhi': ('zh', 'i'), 'chi': ('ch', 'i'), 'shi': ('sh', 'i'), 'ri': ('r', 'i'),
        }
        
        if pinyin_no_tone in special_map:
            return special_map[pinyin_no_tone][0], special_map[pinyin_no_tone][1], tone

        if pinyin_no_tone.startswith('y'):
            if pinyin_no_tone == 'yi':
                return '', 'i', tone
            elif pinyin_no_tone == 'yu' or pinyin_no_tone == 'yv':
                return '', 'ü', tone
            elif pinyin_no_tone.startswith('yu'):
                return '', 'ü' + pinyin_no_tone[2:], tone
            else:
                return '', 'i' + pinyin_no_tone[1:], tone
        elif pinyin_no_tone.startswith('w'):
            if pinyin_no_tone == 'wu':
                return '', 'u', tone
            else:
                return '', 'u' + pinyin_no_tone[1:], tone
            
        


        initials = ['b', 'p', 'm', 'f', 'd', 't', 'n', 'l', 'g', 'k', 'h',
                   'j', 'q', 'x', 'zh', 'ch', 'sh', 'r', 'z', 'c', 's']

        if len(pinyin_no_tone) >= 2 and pinyin_no_tone[:2] in ['zh', 'ch', 'sh']:
            initial = pinyin_no_tone[:2]
            final = pinyin_no_tone[2:]
        elif pinyin_no_tone and pinyin_no_tone[0] in initials:
            initial = pinyin_no_tone[0]
            final = pinyin_no_tone[1:]
        else:
            initial = ''
            final = pinyin_no_tone

        if initial in ['j', 'q', 'x'] and final.startswith('u'):
            final = 'ü' + final[1:]
        
        return initial, final, tone
    
    def get_braille_for_initial(self, initial):
        if not initial:
            return [0,0,0,0,0,0]
        return self.initials_braille.get(initial)

    def get_braille_for_final(self, final):
        return self.finals_braille.get(final)

    def get_braille_for_tone(self, tone):
        return self.tones_braille.get(tone)

    @staticmethod
    def _flip_dots(dots: list) -> list:
        if not dots or len(dots) != 6:
            return dots
        return [dots[3], dots[4], dots[5], dots[0], dots[1], dots[2]]

    def convert_single_character(self, char: str) -> dict:
        pinyin_str = self.chinese_to_pinyin(char)[0]
        initial, final, tone = self.parse_pinyin(pinyin_str)
        
        result = {
            'character': char,
            'pinyin': pinyin_str,
            'initial': initial,
            'final': final,
            'tone': tone,
            'braille_initial': [],
            'braille_final': [],
            'braille_tone': [],
        }

        if initial:
            result['braille_initial'] = self.get_braille_for_initial(initial)
        result['braille_final'] = self.get_braille_for_final(final)
        result['braille_tone'] = self.get_braille_for_tone(tone)

        if self._flip_dots_enabled:
            if result['braille_initial']:
                result['braille_initial'] = self._flip_dots(result['braille_initial'])
            result['braille_final'] = self._flip_dots(result['braille_final'])
            result['braille_tone'] = self._flip_dots(result['braille_tone'])
        
        return result
    
    def convert_text(self, text: str) -> list:
        results = []
        for char in text:
            if char.strip():
                result = self.convert_single_character(char)
                results.append(result)
        return results

    def format_braille_dots(self, dots: list) -> str:
        if not dots:
            return "无"
        return f"[{dots[0]}{dots[1]}{dots[2]}{dots[3]}{dots[4]}{dots[5]}]"

    def visualize_braille(self, dots: list) -> str:
        if not dots:
            return "无"
        
        grid = [
            ['●' if dots[0] else '○', '●' if dots[3] else '○'],
            ['●' if dots[1] else '○', '●' if dots[4] else '○'],
            ['●' if dots[2] else '○', '●' if dots[5] else '○']
        ]
        
        visualization = ""
        for row in grid:
            visualization += f"  {row[0]}  {row[1]}\n"
        return visualization.rstrip()

    def keep_only_chinese(self, text: str) -> str:
        return ''.join(re.findall(r'[\u4e00-\u9fff]', text))


if __name__ == "__main__":
    converter = ChineseToBraille()
    
   
    test_text = converter.keep_only_chinese("你好世界")
    results = converter.convert_text(test_text)
    for result in results:
        print(f"字符:{result['character']}")
        print(f"拼音:{result['pinyin']} ")
       
        print(f"声母盲文点位:{converter.format_braille_dots(result['braille_initial'])}")
        print(f"韵母盲文点位:{converter.format_braille_dots(result['braille_final'])}")
        print(f"声调盲文点位:{converter.format_braille_dots(result['braille_tone'])}")
    
        print("声母盲文可视化:")
        print(converter.visualize_braille(result['braille_initial']))
        print("韵母盲文可视化:")
        print(converter.visualize_braille(result['braille_final']))
        print("声调盲文可视化:")
        print(converter.visualize_braille(result['braille_tone']))
        print("-" * 30)

        sys.stdout.flush()
    