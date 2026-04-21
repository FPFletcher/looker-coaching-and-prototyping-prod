import json

data = {
  "type": "service_account",
  "project_id": "antigravity-innovations",
  "private_key_id": "a1a63cadb64113cb4806f6a72369d1f69e332752",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDNMfOqBQ8WuEt0\n/7fnBsaz78tH1UcLkNkP+ehO2bEqzfjp6jPrlEX/24Ylgi8sE5aXwX4JXuLt0SSU\nwXFs6mTgOUz2pi/1/dK1xQnNcPzuVJ4SEXxeHOxCN+q2mBhiIBL1h/43/tJfCc9f\n2wVym4zzhSf7UoYar7C7S4A20A2DbqTo92modo8WR2ES1/ZJXsvX414hEK5YYr4m\nr7oruva3WQSE7wNbMbbcItZDl9jj+lExmE1s0l9PSB3Cujzyv5OIkB6sy4UmCsBa\nju/j6wnXYHR0ceIKO6i3WJeTrbVP6e5Of0qSxnkAGVS6s2HWYTCiboDP4tozgUvg\n2MXB9ad5AgMBAAECggEAA+bO32Uaevf83lAE8Qh+03nMI5TldY225N//d+1ZeisB\nsD/u5gwzEwj7aV/q8fN65e6MzRSP683x3D6734Jq8d0BDsEM8ShW/vQMykpbUtRK\nz6TjuJ3j66Poy3lDoG0D80V3Utz+ZsZ22hed6EaXJOO7pYKVkHEWAw+t08z7rsut\ncUDOXaja8nR8u/BwKwd/nDBWaA0BGdD2bA0KNstcYkJa7E+OUG8UW5S0sLT4xIXI\nLRVJKee9IXfuNTytSh+4VGDK+qAYHneeurcKQEB4uC5mKsT8bpwhE85qLZPELcTD\nLVfWB75IMI5Sp6rANO2o39Sym9QNnaI6mq4+F838oQKBgQDovHHKKSMc9rvFUy9h\nJ47+fjgX2smPNcXAzu0PE2SzeiFjvQD9vX2KfzjPd7IJEahr18QVlLo8KXUMv5Nk\nRRxXsfFkFxT66UJh23Xm8FDB2gcu4xmtUdvV1FjQ2A7TiNDnEson53bQkk2YEv4i\nO1m4KkI2Gz/udlncmiHN6Pt7mQKBgQDhtMCpZByL6zlKxTITJgpSsRFHryVfhnFJ\nCyPp95R/xFh8diuTclO84Whqz4/xxWsmRV7CoPrupEixtODWnQvwZa5/8wsapZvt\nvts0mSorgVfdZv48C3ySeEa7dhDl7j7djyngEM9TNLUfCSfh6k3L088JMQvpG1pi\nr6W7dxH24QKBgQCpuSs+Y2uQ5roed8B4mHGmVAOyGcKdpng1WHH2aY0peao54w6C\n/Jo90vNqEP8LsA3jv3Dm0BRUZWNPzbG+EMxPg5vnAxIwvMTFOlcr+Brck5RjdAg4\phasRHQUsUt2pjK6ILC+EwVJqzfc7BTaf++451BrxsmDrFlyEBEQ6ZPkGQKBgFdV\nyMMC4OTnRQkAmuq76nyq1WPmitCWxhkcfW4YBdcWk6K9Wwk30N0iX3QNEsbbvCVX\n7F3lSpOy8AoLUoDYzfjcb5RE6EQMVvS8yDdnGOEysFwUcUWssCxA7CW3frxp3tt+\nfRadiovItljnAw6wyh+XuuH0n4Y4tlW/X6LVZRchAoGACC7fP2eyQuQWjjPpUrBG\nwa9asFZjNkuwJudyiZAd4dztYp6zIlbn1SZtLJHaDvjr2pohl6ijux96xBWDRdIe\nJ0vlM64/QMiTbRVeuORoZlFj1112NENNG6XSMotuqD6BOw0SOSCXSfX78OOLy9+e\nyr59X4dLAOApm7b3DM8F8NQ=\n-----END PRIVATE KEY-----\n",
  "client_email": "looker-vertex-agent@antigravity-innovations.iam.gserviceaccount.com",
  "client_id": "111424775289288248762",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/looker-vertex-agent%40antigravity-innovations.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# Convert \n text to real newlines
pk = data["private_key"]
pk = pk.replace("\\n", "\n")

# Split into lines to isolate body
lines = pk.split("\n")
lines = [l for l in lines if l]
if len(lines) > 2:
    header = lines[0]
    footer = lines[-1]
    body = "".join(lines[1:-1])
    # Remove ANY remaining backslashes from the body
    body = body.replace("\\", "")
    # Reconstruct with real newlines
    data["private_key"] = f"{header}\n{body}\n{footer}\n"

with open('vertex-sa-key.json', 'w') as f:
    json.dump(data, f, indent=2)
print("Successfully wrote vertex-sa-key.json with clean private key")
