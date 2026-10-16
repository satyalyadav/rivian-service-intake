"""Curated synthetic conversations with checked live model results."""

examples: list[dict] = [
    {
        "id": "noise-over-bumps",
        "title": "Noise over bumps",
        "description": "A complete call that ends with a booked visit and a full write-up.",
        "transcript": (
            "Advisor: Rivian service, this is Maya. How can I help you today?\n"
            "Customer: Hi, I'm calling about my R1S. It's been making a creaking sound when I go over speed bumps.\n"
            "Advisor: When did you first notice it?\n"
            "Customer: About two weeks ago. It's usually worse in the mornings.\n"
            "Advisor: How often does it happen now?\n"
            "Customer: Every time I go over a bump, so at least a few times a day.\n"
            "Advisor: Does it come from the front or the rear?\n"
            "Customer: The front, I think, and mostly on the left side.\n"
            "Advisor: Does it happen at higher speeds too?\n"
            "Customer: On the highway it's quiet. It's really only at low speeds.\n"
            "Advisor: Has any suspension work been done recently?\n"
            "Customer: No suspension work, this is the first issue the truck has had.\n"
            "Advisor: What's the mileage on it?\n"
            "Customer: The odometer shows 28,410 miles.\n"
            "Advisor: Thanks. Do you want to bring it in this week?\n"
            "Customer: Yes, Friday morning would be great if you have a slot.\n"
            "Advisor: We have Friday at nine. I'll get you booked in.\n"
            "Customer: Perfect, thank you.\n"
        ),
        "vehicle": {"model": "R1S", "year": "2023"},
        "result": {
            "facts": [
                {
                    "id": "F1",
                    "field": "concern",
                    "value": "creaking sound when I go over speed bumps",
                    "evidence": [
                        {
                            "turn_id": "T2",
                            "speaker": "Customer",
                            "quote": "creaking sound when I go over speed bumps"
                        }
                    ]
                },
                {
                    "id": "F2",
                    "field": "timing",
                    "value": "two weeks ago",
                    "evidence": [
                        {
                            "turn_id": "T4",
                            "speaker": "Customer",
                            "quote": "two weeks ago"
                        }
                    ]
                },
                {
                    "id": "F3",
                    "field": "frequency",
                    "value": "at least a few times a day",
                    "evidence": [
                        {
                            "turn_id": "T6",
                            "speaker": "Customer",
                            "quote": "at least a few times a day"
                        }
                    ]
                },
                {
                    "id": "F4",
                    "field": "location",
                    "value": "The front",
                    "evidence": [
                        {
                            "turn_id": "T8",
                            "speaker": "Customer",
                            "quote": "The front"
                        }
                    ]
                },
                {
                    "id": "F5",
                    "field": "location",
                    "value": "left side",
                    "evidence": [
                        {
                            "turn_id": "T8",
                            "speaker": "Customer",
                            "quote": "left side"
                        }
                    ]
                },
                {
                    "id": "F6",
                    "field": "conditions",
                    "value": "only at low speeds",
                    "evidence": [
                        {
                            "turn_id": "T10",
                            "speaker": "Customer",
                            "quote": "only at low speeds"
                        }
                    ]
                },
                {
                    "id": "F7",
                    "field": "conditions",
                    "value": "worse in the mornings",
                    "evidence": [
                        {
                            "turn_id": "T4",
                            "speaker": "Customer",
                            "quote": "worse in the mornings"
                        }
                    ]
                },
                {
                    "id": "F8",
                    "field": "mileage",
                    "value": "28,410 miles",
                    "evidence": [
                        {
                            "turn_id": "T14",
                            "speaker": "Customer",
                            "quote": "28,410 miles"
                        }
                    ]
                },
                {
                    "id": "F9",
                    "field": "service_history",
                    "value": "No suspension work",
                    "evidence": [
                        {
                            "turn_id": "T12",
                            "speaker": "Customer",
                            "quote": "No suspension work"
                        }
                    ]
                },
                {
                    "id": "F10",
                    "field": "other_detail",
                    "value": "this is the first issue the truck has had",
                    "evidence": [
                        {
                            "turn_id": "T12",
                            "speaker": "Customer",
                            "quote": "this is the first issue the truck has had"
                        }
                    ]
                }
            ],
            "corrections": [],
            "conflicts": [],
            "questions": [
                "Does the creaking happen only when going straight over bumps, or also when turning over bumps?",
                "Does the creaking change after the vehicle has been driven for a while or in different temperatures?",
                "What is the VIN?"
            ]
        }
    },
    {
        "id": "correction-and-conflict",
        "title": "Correction and a mileage conflict",
        "description": "The customer corrects the timeline, and the mileage on file disagrees with the odometer.",
        "transcript": (
            "Advisor: Rivian service, this is Devon. What can I do for you?\n"
            "Customer: My R1T has a rattle coming from the dash, and it's getting worse.\n"
            "Advisor: When did you first notice the rattle?\n"
            "Customer: Around three weeks ago, I think.\n"
            "Advisor: Is it constant, or is something triggering it?\n"
            "Customer: It shows up on rough roads. On smooth pavement it's quiet.\n"
            "Advisor: Does it change when the cabin warms up?\n"
            "Customer: No, it doesn't matter if it's hot or cold.\n"
            "Advisor: Has the dash been apart for any recent work?\n"
            "Customer: No, the dash has never been apart. Actually I checked my calendar, it's been closer to four weeks, so almost a month.\n"
            "Advisor: Thanks for checking. What's the current mileage?\n"
            "Customer: The odometer reads 41,000 miles.\n"
            "Advisor: When I pull up the service file, it lists 47,000 miles.\n"
            "Customer: That's odd. The odometer is what I look at every day.\n"
            "Advisor: I'll note both. Would you like us to look at the rattle?\n"
            "Customer: Yes, next Tuesday if you have an opening.\n"
            "Advisor: We do. I'll put the rattle on the ticket.\n"
        ),
        "vehicle": {"model": "R1T"},
        "result": {
            "facts": [
                {
                    "id": "F1",
                    "field": "concern",
                    "value": "rattle",
                    "evidence": [
                        {
                            "turn_id": "T2",
                            "speaker": "Customer",
                            "quote": "rattle"
                        }
                    ]
                },
                {
                    "id": "F2",
                    "field": "location",
                    "value": "the dash",
                    "evidence": [
                        {
                            "turn_id": "T2",
                            "speaker": "Customer",
                            "quote": "from the dash"
                        }
                    ]
                },
                {
                    "id": "F3",
                    "field": "other_detail",
                    "value": "getting worse",
                    "evidence": [
                        {
                            "turn_id": "T2",
                            "speaker": "Customer",
                            "quote": "getting worse"
                        }
                    ]
                },
                {
                    "id": "F4",
                    "field": "conditions",
                    "value": "on rough roads",
                    "evidence": [
                        {
                            "turn_id": "T6",
                            "speaker": "Customer",
                            "quote": "on rough roads"
                        }
                    ]
                },
                {
                    "id": "F5",
                    "field": "conditions",
                    "value": "doesn't matter if it's hot or cold",
                    "evidence": [
                        {
                            "turn_id": "T8",
                            "speaker": "Customer",
                            "quote": "it doesn't matter if it's hot or cold"
                        }
                    ]
                },
                {
                    "id": "F6",
                    "field": "service_history",
                    "value": "the dash has never been apart",
                    "evidence": [
                        {
                            "turn_id": "T10",
                            "speaker": "Customer",
                            "quote": "the dash has never been apart"
                        }
                    ]
                },
                {
                    "id": "F7",
                    "field": "timing",
                    "value": "closer to four weeks",
                    "evidence": [
                        {
                            "turn_id": "T10",
                            "speaker": "Customer",
                            "quote": "closer to four weeks"
                        }
                    ]
                }
            ],
            "corrections": [
                {
                    "field": "timing",
                    "previous_value": "Around three weeks ago",
                    "current_value": "closer to four weeks",
                    "evidence": [
                        {
                            "turn_id": "T4",
                            "speaker": "Customer",
                            "quote": "Around three weeks ago"
                        },
                        {
                            "turn_id": "T10",
                            "speaker": "Customer",
                            "quote": "closer to four weeks"
                        }
                    ]
                }
            ],
            "conflicts": [
                {
                    "field": "mileage",
                    "values": [
                        "41,000 miles",
                        "47,000 miles"
                    ],
                    "evidence": [
                        {
                            "turn_id": "T12",
                            "speaker": "Customer",
                            "quote": "41,000 miles"
                        },
                        {
                            "turn_id": "T13",
                            "speaker": "Advisor",
                            "quote": "47,000 miles"
                        }
                    ]
                }
            ],
            "questions": [
                "The odometer reading you gave and the mileage in the service file don't match \u2014 can you confirm the reading on the odometer today?",
                "Which part of the dash does the rattle seem to come from?",
                "Does the rattle happen every time you drive on rough roads?"
            ]
        }
    },
    {
        "id": "messy-call",
        "title": "One concern inside a messy call",
        "description": "Small talk and a side question surround one real audio concern.",
        "transcript": (
            "Advisor: Rivian service, this is Priya speaking.\n"
            "Customer: Hi! Quick question while I have you, is the car wash on Route 9 still open?\n"
            "Advisor: I'm not sure about that one. Are you calling about your vehicle today?\n"
            "Customer: Right, sorry. The radio in my R1S keeps cutting out, it's been happening for a couple of days.\n"
            "Advisor: Does it cut out on every source, or just FM?\n"
            "Customer: Bluetooth too. My phone disconnects and reconnects while I'm driving.\n"
            "Advisor: Does the screen stay on when the audio drops?\n"
            "Customer: The screen is fine. It's only the sound that goes.\n"
            "Advisor: How many times does it happen in a drive?\n"
            "Customer: Two or three times in a half hour drive, pretty much every trip since Monday.\n"
            "Advisor: Anything else unusual with the truck?\n"
            "Customer: No, everything else is normal. My partner washed it on Saturday, if that matters.\n"
            "Advisor: Any water get inside that you noticed?\n"
            "Customer: The mats were dry when I checked.\n"
            "Advisor: Let's have the audio looked at. Does Thursday afternoon work?\n"
            "Customer: Thursday works for me.\n"
            "Advisor: Great. I'll add the radio concern to the ticket.\n"
        ),
        "vehicle": {},
        "result": {
            "facts": [
                {
                    "id": "F1",
                    "field": "concern",
                    "value": "The radio in my R1S keeps cutting out",
                    "evidence": [
                        {
                            "turn_id": "T4",
                            "speaker": "Customer",
                            "quote": "The radio in my R1S keeps cutting out"
                        }
                    ]
                },
                {
                    "id": "F2",
                    "field": "model",
                    "value": "R1S",
                    "evidence": [
                        {
                            "turn_id": "T4",
                            "speaker": "Customer",
                            "quote": "my R1S"
                        }
                    ]
                },
                {
                    "id": "F3",
                    "field": "timing",
                    "value": "for a couple of days",
                    "evidence": [
                        {
                            "turn_id": "T4",
                            "speaker": "Customer",
                            "quote": "it's been happening for a couple of days"
                        }
                    ]
                },
                {
                    "id": "F4",
                    "field": "conditions",
                    "value": "My phone disconnects and reconnects while I'm driving",
                    "evidence": [
                        {
                            "turn_id": "T6",
                            "speaker": "Customer",
                            "quote": "My phone disconnects and reconnects while I'm driving"
                        }
                    ]
                },
                {
                    "id": "F5",
                    "field": "conditions",
                    "value": "only the sound that goes",
                    "evidence": [
                        {
                            "turn_id": "T8",
                            "speaker": "Customer",
                            "quote": "It's only the sound that goes"
                        }
                    ]
                },
                {
                    "id": "F6",
                    "field": "frequency",
                    "value": "Two or three times in a half hour drive",
                    "evidence": [
                        {
                            "turn_id": "T10",
                            "speaker": "Customer",
                            "quote": "Two or three times in a half hour drive"
                        }
                    ]
                },
                {
                    "id": "F7",
                    "field": "timing",
                    "value": "since Monday",
                    "evidence": [
                        {
                            "turn_id": "T10",
                            "speaker": "Customer",
                            "quote": "pretty much every trip since Monday"
                        }
                    ]
                },
                {
                    "id": "F8",
                    "field": "other_detail",
                    "value": "My partner washed it on Saturday",
                    "evidence": [
                        {
                            "turn_id": "T12",
                            "speaker": "Customer",
                            "quote": "My partner washed it on Saturday"
                        }
                    ]
                },
                {
                    "id": "F9",
                    "field": "other_detail",
                    "value": "The mats were dry",
                    "evidence": [
                        {
                            "turn_id": "T14",
                            "speaker": "Customer",
                            "quote": "The mats were dry"
                        }
                    ]
                }
            ],
            "corrections": [],
            "conflicts": [],
            "questions": [
                "Does the audio drop in the same way when the vehicle is parked, or only while you are driving?",
                "Does the sound come back on its own, or do you have to change the source to get it back?",
                "Does anything appear on the screen or a warning light come on when the sound drops?"
            ]
        }
    },
    {
        "id": "missing-details",
        "title": "Missing details and open questions",
        "description": "A tire pressure warning with no readings known and no identifiers on hand.",
        "transcript": (
            "Advisor: Rivian service, this is Sam.\n"
            "Customer: Hi, a tire pressure warning came on this morning when I started the car.\n"
            "Advisor: Does it say which tire?\n"
            "Customer: It just shows the warning symbol. There's no number or anything.\n"
            "Advisor: Have you checked the pressures with a gauge?\n"
            "Customer: No, I don't have one at home.\n"
            "Advisor: Does the warning stay on while you drive?\n"
            "Customer: Yes, it hasn't gone away all day.\n"
            "Advisor: How cold has it been overnight?\n"
            "Customer: It's been in the twenties. The truck sits outside.\n"
            "Advisor: Do you know the current mileage?\n"
            "Customer: I'd have to look. I don't remember the number.\n"
            "Advisor: No problem. Can you read me the VIN from the dashboard?\n"
            "Customer: Hold on... I can't find it right now, sorry. I can text it to you later.\n"
            "Advisor: That works. We'll check the tire pressures when you come in tomorrow.\n"
        ),
        "vehicle": {},
        "result": {
            "facts": [
                {
                    "id": "F1",
                    "field": "concern",
                    "value": "tire pressure warning came on",
                    "evidence": [
                        {
                            "turn_id": "T2",
                            "speaker": "Customer",
                            "quote": "a tire pressure warning came on"
                        }
                    ]
                },
                {
                    "id": "F2",
                    "field": "timing",
                    "value": "this morning",
                    "evidence": [
                        {
                            "turn_id": "T2",
                            "speaker": "Customer",
                            "quote": "this morning"
                        }
                    ]
                },
                {
                    "id": "F3",
                    "field": "warning",
                    "value": "just shows the warning symbol",
                    "evidence": [
                        {
                            "turn_id": "T4",
                            "speaker": "Customer",
                            "quote": "It just shows the warning symbol"
                        }
                    ]
                },
                {
                    "id": "F4",
                    "field": "frequency",
                    "value": "hasn't gone away all day",
                    "evidence": [
                        {
                            "turn_id": "T8",
                            "speaker": "Customer",
                            "quote": "it hasn't gone away all day"
                        }
                    ]
                },
                {
                    "id": "F5",
                    "field": "conditions",
                    "value": "in the twenties",
                    "evidence": [
                        {
                            "turn_id": "T10",
                            "speaker": "Customer",
                            "quote": "It's been in the twenties"
                        }
                    ]
                },
                {
                    "id": "F6",
                    "field": "other_detail",
                    "value": "sits outside",
                    "evidence": [
                        {
                            "turn_id": "T10",
                            "speaker": "Customer",
                            "quote": "The truck sits outside"
                        }
                    ]
                }
            ],
            "corrections": [],
            "conflicts": [],
            "questions": [
                "Can you get a tire-pressure gauge reading for each of the four tires before tomorrow's visit, or have the pressures measured when you arrive?",
                "Do you know when the tire pressures were last checked, or whether any tire has needed air recently?",
                "Can you text the VIN and the current odometer reading before your visit?"
            ]
        }
    },
]
