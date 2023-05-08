def get_voice_menu(voices_info, recommended_voices):
    gender_emojis = { 'm': '👨👨👨', 'f': '👩👩👧' }
    male_count, female_count = (0, 0)
    voice_menu = []
    for role in recommended_voices:
        gender = voices_info[role][-1]
        index = male_count if gender == 'm' else female_count
        lang = '（英文）' if voices_info[role][-2] == 'en' else '（中文）'
        voice_menu.append({
            'type': 'click',
            'name': f'{gender_emojis[gender][index]}{role}{lang}',
            'key': f'voice:{role}',
        })
        if gender == 'm': male_count += 1
        else: female_count += 1
    return voice_menu

def get_wx_menu(voice_menu):
    return {
        'button': [
            {
                'name': '👍🏻支持',
                'sub_button':[
                    {
                        'type': 'click',
                        'name': '打赏作者',
                        'key': 'show-pay-qrcode',
                    },
                    {
                        'type': 'click',
                        'name': '讨论交流',
                        'key': 'show-group-chat-qrcode',
                    },
                    {
                        'type': 'click',
                        'name': '我的等级',
                        'key': 'show-level',
                    },
                    {
                        'type': 'click',
                        'name': '升级额度',
                        'key': 'upgrade',
                    },
                ],
            },
            {
                'name': '🎙️语音',
                'sub_button': voice_menu,
            },
            {
                'type': 'click',
                'name': '🎨绘画',
                'key': 'ai-draw',
            },
        ]
    }