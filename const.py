import os
from pathlib import Path

runtime_tmp_dir = ''
APP_PATH = os.path.dirname(__file__)

if os.name == 'nt':
    runtime_tmp_dir = os.path.join('C:\\', 'Recorder')
if os.name == 'posix' and os.uname().sysname == 'Linux':
    runtime_tmp_dir = os.path.join('/var', '.Recorder')
if os.name == 'posix' and os.uname().sysname == 'Darwin':
    runtime_tmp_dir = os.path.join(Path.home(), '.Recorder')


if not os.path.exists(runtime_tmp_dir):
    os.makedirs(runtime_tmp_dir)

API_TOKEN='trackeradmin'

prevent_list = [
    "rodong.rep.kp",
    "kcna.kp",
    "vok.rep.kp",
    "mediaryugyong.com.kp",
    "naenara.com.kp",
    "pyongyangtimes.com.kp",
    "korean-books.com.kp",
    "mfa.gov.kp",
    "ryongnamsan.edu.kp",
    "kftrade.com.kp",
    "friend.com.kp",
    "kut.edu.kp",
    "kass.org.kp",
    "youth.rep.kp",
    "manmulsang.com.kp",
    "fia.law.kp",
    "koredufund.org.kp",
    "kiyctc.com.kp",
    "cooks.org.kp",
    "knic.com.kp",
    "korelcfund.org.kp",
    "tourismdprk.gov.kp",
    "mirae.aca.kp",
    "ma.gov.kp",
    "sdprk.org.kp",
    "korfilm.com.kp",
    "yongsaeng.org.kp",
    "naenara.com.kp/sites/kfpd",
    "naenara.com.kp/sites/kgf",
    "gpsh.edu.kp",
    "minzu.rep.kp",
    "ryomyong.edu.kp",
    "moph.gov.kp",
    "korart.sca.kp",
    "naenara.com.kp",
    "korstamp.com.kp",
    "dprkportal.kp",
    "로동신문",
    "조선중앙통신",
    "조선의 소리",
    "류경",
    "내나라",
    "평양시보",
    "조선의 출판물",
    "조선민주주의인민공화국 외무성",
    "김일성종합대학",
    "조선의 무역",
    "벗",
    "김책공업종합대학",
    "주체",
    "청년전위",
    "만물상",
    "조선민주주의인민공화국 금융정보국",
    "조선교육후원기금",
    "조선국제청소년려행사",
    "조선료리",
    "조선민족보험총회사",
    "로인들을 위하여",
    "조선관광",
    "미래",
    "국가해사감독국",
    "조선체육",
    "조선영화",
    "영생",
    "희망",
    "조선록색후원기금",
    "남산",
    "민주조선",
    "려명",
    "인민보건",
    "조선예술",
    "조선민족유산보호기금",
    "조선우표",
    "조선민주주의인민공화국",
    "Korean Film",
    "PyongyangTimes"
]

CLIENT_VERSION = "0.2.5"

STREAM_STATUS = {
    "IDLE": "idle",
    "STARTING": "starting",
    "STREAMING": "streaming",
    "STOPPING": "stopping",
}

server_ip = '192.168.0.177'
