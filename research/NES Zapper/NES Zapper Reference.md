# The NES Zapper


## 1. History

### Light Guns

In 1970 Nintendo was still mostly making toys and playing cards, and it launched a line called Kōsenjū SP. These were plastic guns that fired a beam of light at plastic targets with photocells in them. Hit the sensor on the target and it falls over. Gunpei Yokoi was the project lead.

Masayuki Uemura introduced the technology to Nintendo. He had been selling photocells and solar cells for Sharp before Nintendo hired him away in 1971. He is generally credited with the optoelectronics that made the toy line practical, and he went on to help design the Famicom.

### Laser Clay, 1973

Nintendo President, Hiroshi Yamauchi, was interested in competitive shooting and decided Nintendo should build a full-size light gun version of the idea. Yokoi again was put on the project and did the engineering, the project was approved in 1973, and the Laser Clay Shooting System went into Japanese bowling alleys. Bowling had been a fad and the fad had ended, so the country was full of large empty buildings with nothing in them. The Laser Clay Shooting System used an overhead 16mm projector that drew clay pigeon targets onto a wide screen painted with mountains and forest, and reflected light told the machine whether you'd hit.

The first few weeks were a hit. Test locations ran at capacity. Then the oil crisis arrived at the end of 1973 and Nintendo was left with a large debt.

Yokoi's solution was to shrink the product. Mini Laser Clay, in 1974, put the same idea in a single arcade cabinet. Those sold, the debt came down, and the format produced a handful of gun games. A few of which I'm sure you'll recognize, but not necessarily the way you know them.

- **Wild Gunman** (1974
- **Shooting Trainer** (1976)
- **Duck Hunt** (1976)

### The Famicom gun, 1984

Nintendo first brought the light gun to video games about fourteen months after the Famicom launched. The Ray Gun, a realistic looking revolver, arrived in February 1984 with a Famicom version of *Wild Gunman* in the box and a holster belt to hang the toy gun off.

Yokoi and Satoru Okada designed it, and they modeled it closely on the American designed, Colt Single Action Army. It has a hammer that moves, and pulling the trigger makes a loud mechanical crack. It plugs into the Famicom's expansion port rather than a controller port, which is why no Famicom game ever supported two guns.

Unlike the continued support that the Zapper line saw in North America, only three games shipped in the series, all in 1984: *Wild Gunman* on February 18th, *Duck Hunt* on April 21st, *Hogan's Alley* on June 12th. Anything after came from third parties.

### The arcade versions

Nintendo shipped gun versions of its own games into arcades at the same time, on the Vs. System (*Vs. Duck Hunt*, *Vs. Hogan's Alley*, *Vs. Gumshoe*, *Vs. Freedom Force*) and on PlayChoice-10 cabinets. The Vs. hardware runs the same protocol with one difference: the light-sense bit is inverted, so 1 means light detected instead of 0. Some Vs. versions have more content than the console games. *Vs. Duck Hunt* lets you shoot the dog.

### The Zapper, 1985

As plans for the Nintendo Entertainment System began, they focused efforts on a complete package that made the NES seem like more than the previous generations consoles. Nintendo of America's head designer, Lance Barr, had the job of redrawing the peripheral for the US launch. Perhaps to the surprise of no one, the idea of a realistic revolver going into American toy stores, attached to a console whose entire marketing strategy was pretending not to be a video game console, required a heavy redesign. Barr kept the guts and replaced the shell with a sci-fi style laser gun matching the NES's gray and black.

The gray Zapper (NES-005) went on sale with the console in New York on October 18th 1985, packed into the Deluxe Set with R.O.B., two controllers, *Duck Hunt* and *Gyromite*.

### The Orange Zapper, 1989

In 1988, Section 4 of the Federal Energy Management Improvement Act (now 15 U.S.C. § 5001) made it illegal to manufacture, ship or sell a toy or look-alike firearm in the US without an approved marking. The Commerce Department regulations took effect on May 5th 1989 and applied to anything entering commerce from that date forward.

Nintendo recolored instead of redesigning. A revised NES-005 with an orange barrel and orange grip showed up in 1989, same electronics, same model number. Because the change happened mid-generation both colors are common. I personally grew up on an orange zapper.

### The End of the Zapper

Third-party support dried up by 1992. *Day Dreamin' Davey* is the last NES game with any Zapper code in it, and Nintendo moved on to the Super Scope for the SNES.

Experiencing the Zapper today is not easy. The Zapper can only work on a CRT. LCD, plasma and OLED sets all introduce processing lag and none of them produce the scanning beam the gun is built to detect.


---

## 2. How it works

### The Trick

A CRT paints its picture with one moving dot of light that sweeps left to right, top to bottom, about sixty times a second. At any given instant only one small spot on the screen is actually lit. So if the game knows what it drew and when, and the gun says "I saw light just now," the game can work out where you were pointing.

### What happens when you pull the trigger

All of this takes a few frames and that's why you'll see a flicker on your TV after a shot.

1. The game reads the trigger bit during normal play.
2. It blanks the whole screen to black for one frame and checks the sensor. If the gun reports light while the screen is black, it isn't aimed at the TV. The shot counts as a miss. This is why you can't just shoot a lightbulb and register a hit.
3. On the next frame it draws exactly one valid target as a solid white box on the black screen and checks the sensor again. Light means you hit that target.
4. If there are two targets, it does step 3 twice, in a known order, so it can tell which one you got.
5. Normal gameplay resumes.

Some games add an all-white frame at the start to confirm you're pointed at the screen at all before running the sequence.

### The parts

**Optics.** There's a lens at the end of a long tube in the barrel, with two orange occluders narrowing the photodiode's view, plus a weight that exists purely so the gun feels like something. This narrow scope is why you should play from three feet back and why the gun is so forgiving about sloppy aim.

**Filtering.** The photodiode circuit is tuned to respond around 15 kHz, which is essentially the NTSC horizontal scan rate. That's the ambient light rejection: a bulb or daylight varies slowly or not at all and gets attenuated, while a CRT's line-by-line flicker goes straight through. It's also the single biggest reason the gun is dead on modern displays, which produce no such signal.

**Trigger.** Not a simple switch. It reads 0 when fully open, 1 when half pulled, and 0 again once you pull it all the way to the clunk.

---

## 3. Variants

### Nintendo's

**Famicom Ray Gun, HVC-005.** Japan, 18 February 1984. Gray and black, modeled on a Colt Single Action Army, working hammer, loud crack when you pull the trigger. Sold with *Wild Gunman* and a holster belt.

**Vs. System gun.** Arcade, from 1984. Cabinet-mounted or holstered, used on Vs. UniSystem and DualSystem boards.

**NES Zapper, gray, NES-005.** North America, 18 October 1985, Europe from 1986 to 1987. Barr's ray gun redesign in NES light gray.

**PlayChoice-10 gun.** Arcade, from 1986. Fitted to PC10 cabinets running gun games like *Duck Hunt* and *Hogan's Alley*.

**NES Zapper, orange, NES-005.** 1989. Same electronics, same model number, orange barrel and grip to satisfy US imitation firearm marking rules. This is the one in most later Action Sets and Power Sets.

### Everyone else's

**Bandai Hyper Shot**, Famicom, Released in 1989. A submachine gun with battery-powered recoil (Bandai called it the Body Vibration System), a speaker in the body and a D-pad on the side. Sold with *Space Shadow*. It does not work with Nintendo's light gun games and Nintendo's gun does not work with *Space Shadow*. (Need to find out why)

**Konami LaserScope**, Released in 1990. This headset comes with a transparent crosshair that hangs in front of your right eye and detachable headphones. Instead of a trigger you fire by shouting into a microphone. It plugs in as a Zapper substitute and works with any Zapper game. Konami built it for *Laser Invasion*. It triggers on any loud noise and there's an emphasis on loud.

**Dominator Pro Beam Light Gun.** Unlicensed Zapper clone.

**QuickShot QS-132 Sighting Scope.** Not a gun. A scope that clips onto a Zapper you already own.


---

## 5. The Zapper Games

The big one. Around twenty games plus two multicarts.


**Duck Hunt**

- **Year:** October 18th 1985, launch title
- **Developer:** Nintendo R&D1 with Intelligent Systems
- **Publisher:** Nintendo
- **Objective:** A dog scares ducks out of tall grass and you shoot them before they get away. Game A is one duck at a time, Game B is two at once, Game C swaps the ducks for clay pigeons launched away from you. Each round gives you ten targets and a quota that climbs as you go. The dog pops up to hold your kills, or to laugh at you, which is the part everyone remembers.
- **Zapper Implementation:** Three shots per ducks. Each trigger pull blanks the screen and then draws each duck in turn as a white box, so the game knows which bird you got rather than just whether you got one. Game C is harder for a physical reason: the clay pigeon's white box shrinks as it recedes, so you're shooting at a smaller sensor target the longer you wait. In Games A and B a second player can grab a controller and fly the ducks. And while you can't shoot the dog in the NES version, the arcade *Vs. Duck Hunt* lets you.

---

**Hogan's Alley**

- **Year:** October 18th 1985, launch title
- **Developer:** Nintendo R&D1 with Intelligent Systems, directed and designed by Shigeru Miyamoto
- **Publisher:** Nintendo
- **Objective:** A police marksmanship game named after the FBI's real training facility. Cardboard cutouts rotate to face you. Some are gangsters, some are a professor or a woman or a uniformed cop, and it's up to you to sort them out and shoot the gangsters. Mode A is the shooting range against a blank wall. Mode B moves the targets into a street, in windows and doorways. Mode C is a bonus game with tin cans.
- **Zapper Implementation:** One shot per target, and the game punishes hesitating just as hard as it punishes shooting wrong. Hit a civilian and you lose a life. Fail to hit a gangster in time and you lose a life. Later rounds put five targets up at once. The other mode, "Trick Shot," involves shooting a falling can to juggle it onto scoring ledges with limited ammo.

---

**Wild Gunman**

- **Year:** October 18th 1985, launch title
- **Developer:** Nintendo R&D1 with Intelligent Systems
- **Publisher:** Nintendo
- **Objective:** A pixel version of Nintendo's own 1974 arcade machine, which used a 16mm projector and footage of real actors. An outlaw faces you in the street, his eyes flash, a balloon says FIRE!!, and you have some posted number of hundredths of a second to draw. Game A is one outlaw, Game B is two at once, Game C is a gang coming out of saloon windows and doors on a timer similar to Hogan's Alley.
- **Zapper Implementation:** In this game holding your fire is just as important as firing it. Shoot before the prompt and you've lost the duel no matter what you do next.

---

**Gumshoe**

- **Year:** August 1986
- **Developer:** Nintendo R&D1, designed by Yoshio Sakamoto
- **Publisher:** Nintendo
- **Objective:** The weirdest thing Nintendo ever did with the Zapper. Ex-FBI agent Mr. Stevenson has 24 hours to find five Black Panther diamonds and rescue his daughter back from a mob boss called King Dom. Structurally it's a side-scrolling platformer across four levels, you just never touch a D-pad.
- **Zapper Implementation:** Stevenson walks right on his own and never stops. You shoot *him* to make him jump. Everything else you shoot to destroy. Ammo is finite, so every wasted shot is a jump you can't make later, and running out will result in a game over. Red balloons drifting through the level top you back up when you shoot them, and collecting twenty opens hidden bonus areas.

---

**Gotcha! The Sport!**

- **Year:** November 1987
- **Developer:** Atlus
- **Publisher:** LJN
- **Objective:** A licensed tie-in to the 1985 Anthony Edwards movie *Gotcha!* that skips the spy comedy plot entirely and adapts the paintball tournament. Cross a scrolling stage, take the enemy flag on the right, carry it back to your base on the left.
- **Zapper Implementation:** You hold the Zapper in one hand to aim and fire and a standard controller in the other, using the D-pad to scroll the screen. Aiming and movement are completely separate, so you can back up while still covering forward. For many it's awkward to hold both controllers, but its unique approach to controls gives the player movement for the first time.

---

**Freedom Force**

- **Year:** April 1988
- **Developer:** Sunsoft
- **Publisher:** Sunsoft
- **Objective:** A counter-terrorist rail shooter. The screen scrolls through airports and city streets while terrorists and hostages appear in windows, doorways and behind cover. It has a two player mode, unfortunately that just means taking turns.
- **Zapper Implementation:** Shoot the terrorists, don't shoot the hostages. Hits leave a small red splotch on the target's chest, which doubles as feedback on your own accuracy. When an item shows up in the box in the lower right corner of the screen, you shoot the box to collect it, and you get energy, ammo or a weapon upgrade. Between stages there's a hangman-style word game where you shoot letters.

---

**Super Mario Bros. / Duck Hunt**

- **Year:** 1988
- **Developer and publisher:** Nintendo
- **Objective:** The Action Set pack-in. Two full games on one cart with a selector on the title screen.
- **Zapper Implementation:** Same as standalone *Duck Hunt*.

---

**Shooting Range**

- **Year:** June 1989
- **Developer:** Tose
- **Publisher:** Bandai America
- **Objective:** A set of light gun mini-games with an "Old West" carnival theme, plus a level set on the moon if the west gets boring.
- **Zapper Implementation:** You're not shooting the characters. You're shooting red and white bullseye targets mounted on their heads, while an energy meter drains as your combined timer and life bar. Shoot the wrong thing and it drains faster.

---

**To the Earth**

- **Year:** November 1989
- **Developer:** Cirque Verte
- **Publisher:** Nintendo
- **Objective:** A first-person rail shooter traveling inward through the solar system against an alien invasion, with a boss at each planet and an alien called Nemesis waiting near Earth.
- **Zapper Implementation:** Shoot the incoming ships, missiles, bombs and asteroids, and don't shoot friendlies. Every shot you miss drains your shield. The three pickups (a screen-clearing bomb, a comet that makes you briefly invulnerable, and a shield refill) are collected by shooting them.

---

**Barker Bill's Trick Shooting**

- **Year:** August 1990
- **Developer:** Nintendo R&D1
- **Publisher:** Nintendo
- **Objective:** A carnival trick-shot showcase hosted by Barker Bill, a name borrowed from a 1950s Terrytoons character, and his assistant Trixie. Four modes, structured as an exhibition rather than a campaign.
- **Zapper Implementation:** Each mode is a different game. *Balloon Saloon* has you popping drifting balloons for 100 points each while the *Duck Hunt* dog wanders through as a hazard. *Flying Saucers* has Bill and Trixie tossing plates across the screen, worth 100 to 500 points depending on height, and you must not hit Bill, Trixie or the parrot. *Window Pains* drops objects past a wall of windows where closed panes physically block your shot, so you're timing each pull to an opening, scoring 100 at the top row up to 500 at the bottom. *Fun Follies* is all three plus two extra stages, Trixie's Shot and Bill's Thrills, with a slot machine bonus.

---

**Super Mario Bros. / Duck Hunt / World Class Track Meet**

- **Year:** 1990
- **Developer and publisher:** Nintendo
- **Objective:** The Power Set pack-in, adding a Power Pad game to the Action Set cart. North America only.
- **Zapper Implementation:** Same as *Duck Hunt*.

---

### Optional Zapper Games

---

**Operation Wolf**

- **Year:** March 1989
- **Developer:** Taito
- **Publisher:** Taito
- **Objective:** A port of Taito's 1987 arcade hit. Roy Adams fights through six missions to free five hostages. An on rails first person side scroller. The NES version has multiple endings depending on how many hostages make it out.
- **Zapper Implementation:** If you play with the Zapper you point at the screen and shoot like normal. Without it you drag a crosshair around with the D-pad. The enemy counts were not adjusted from the arcade cabinet which had auto fire, so playing this with a Zapper is several minutes of continuous trigger mashing.

---

**The Adventures of Bayou Billy**

- **Year:** June 1989
- **Developer:** Konami
- **Publisher:** Konami
- **Objective:** Konami's Famicom game *Mad City* was renamed **The Adventures of Bayou Billy** and rebuilt for North America with a harder difficulty. Billy West works through the Louisiana bayou to get Annabelle Lane back from Godfather Gordon over nine stages in three formats: side-scrolling brawling for most of it, a jeep driving section in stages 4 and 5, and first-person rail shooting in stages 2 and 7.
- **Zapper Implementation:** The aforementioned stages 2 and 7 allow the use of a zapper and the game asks which controller you want at the start of each. The Zapper is the easier choice here because the controller version makes you drag a crosshair, and pointing is faster than dragging.

---

**Track & Field II**

- **Year:** 1989, February
- **Developer:** Konami
- **Publisher:** Konami
- **Objective:** Konami's sequel was built around the 1988 Seoul games. There are fifteen events including fencing, triple jump, freestyle swimming, high dive, clay pigeon shooting, hammer throw, pole vault, canoeing, archery, hurdles, horizontal bar and arm wrestling, plus two bonus events.
- **Zapper Implementation:** The Clay Pigeon Shooting event, which is the one you'd expect, does not use the Zapper. It only works in the Gun Firing bonus event. 

---

**Mechanized Attack**

- **Year:** June 1990
- **Developer:** SNK
- **Publisher:** SNK
- **Objective:** A port of SNK's 1989 arcade rail shooter, which had an Uzi-shaped gun mounted to the cabinet. One commando against a robot army across five stages, with bullets and grenades tracked separately.
- **Zapper Implementation:** The Zapper gets you closest to the arcade as the controller uses the crosshair method instead. Same caveat as *Operation Wolf*, the enemy density assumes an arcade gun with autofire, so your finger does a lot of work.

---

**Laser Invasion**

- **Year:** June 1991
- **Developer:** Konami
- **Publisher:** Konami
- **Objective:** *Gun Sight* in Japan. Three genres stitched together across four missions. You fly an attack helicopter, pick an equipment loadout, then land and infiltrate on foot through first-person shooting sections and 3D maze corridors. Ambitious for the hardware, and it mostly holds together.
- **Zapper Implementation:** You can only use the Zapper in the on-foot shooting sections where the screen auto-scrolls right and soldiers come at you. This is the game Konami built the LaserScope for, and it supports all three inputs: controller, Zapper, or headset.

---

**The Lone Ranger**

- **Year:** August 1991
- **Developer:** Konami
- **Publisher:** Konami
- **Objective:** Navigate eight areas across four different play styles, an overworld map where Tonto gives you leads and outlaw gangs ambush you, top-down towns where you talk to people, buy ammo and TNT and upgrade your barrel, side-scrolling action stages with platforming, and first-person maze corridors with radar showing where enemies are.
- **Zapper Implementation:** The Zapper is only used in the first-person maze battles, where things come at you from all sides. You can opt to use a controller instead. 

---

**Day Dreamin' Davey**

- **Year:** June 1992
- **Developer:** Sculptured Software
- **Publisher:** HAL America
- **Objective:** The last NES game with any Zapper implementation. A bored kid daydreams through seven scenarios set in Ancient Greece, the Middle Ages and the Wild West, played top-down as an action-adventure with maze-like levels and bosses that each need a particular special weapon.
- **Zapper Implementation:** You can use the Zapper in the Wild West showdown. The view flips to a first-person duel, the outlaw tells you to draw, and you shoot the gun out of his hand. A controller reticle does the same job with the D-pad and A. So it's a flavor option for a single boss fight, which makes for a fairly anticlimactic end to the peripheral's life.


---

### Famicom Exclusive Light Gun Game

**スペースシャドー** (*Space Shadow*)

- **Year:** February 20th 1989
- **Developer:** Bandai
- **Publisher:** Bandai
- **Objective:** An *Aliens*-flavored rail shooter. You walk down an octagonal corridor while things burst out of the side passages and the ceiling. You are armed with a machine gun and grenades.
- **The Peripheral:** Sold with Bandai's Hyper Shot, the submachine gun with battery-powered recoil, a speaker and a D-pad on the body. The Hyper Shot is not compatible with Nintendo's light gun games, and Nintendo's Ray Gun won't run *Space Shadow*.

---

## 6. Totals

| Region | Required | Optional | Total | Unlicensed |
|---|---|---|---|---|
| North America | 12 including 2 multicarts | 8 | 20 | 2 (*Baby Boomer*, *Chiller*) |
| PAL | 7 including 1 multicart | 4 | 11 | 1 (*Chiller*, Australia only) |
| Japan | 3 | 3 | 6 | 0 |

Only five games came out in all three regions: *Duck Hunt*, *Hogan's Alley*, *Wild Gunman*, *Mad City* / *The Adventures of Bayou Billy*, and *Operation Wolf*.

### By year

| Year | Titles |
|---|---|
| 1984 | Wild Gunman, Duck Hunt, Hogan's Alley (Japan) |
| 1985 | Duck Hunt, Hogan's Alley, Wild Gunman (North America) |
| 1986 | Gumshoe |
| 1987 | Gotcha! The Sport! |
| 1988 | Freedom Force, SMB/Duck Hunt, Mad City (Japan) |
| 1989 | Operation Wolf, Bayou Billy, Track & Field II, Shooting Range, Baby Boomer, To the Earth |
| 1990 | Barker Bill's Trick Shooting, Chiller, Mechanized Attack, SMB/DH/WCTM |
| 1991 | Gun Sight / Laser Invasion, The Lone Ranger |
| 1992 | Day Dreamin' Davey |

---

## 7. Sources

**Hardware and history**

- [NES Zapper, Wikipedia](https://en.wikipedia.org/wiki/NES_Zapper)
- [Zapper, NESdev Wiki](https://www.nesdev.org/wiki/Zapper) — the register-level and electrical detail
- [Laser Clay Shooting System, Wikipedia](https://en.wikipedia.org/wiki/Laser_Clay_Shooting_System)
- [光線銃シリーズ, Japanese Wikipedia](https://ja.wikipedia.org/wiki/%E5%85%89%E7%B7%9A%E9%8A%83%E3%82%B7%E3%83%AA%E3%83%BC%E3%82%BA)
- [A quick teardown of the NES Zapper Lightgun, Stay Caffeinated](https://www.staycaffeinated.com/2024/04/26/light-gun-teardown)
- [NES Zapper Experiments #1, beardypig](https://www.beardypig.com/2015/12/11/nes-zapper-experiments-1/)
- [List of NES accessories, Wikipedia](https://en.wikipedia.org/wiki/List_of_Nintendo_Entertainment_System_accessories)
- [LaserScope, Wikipedia](https://en.wikipedia.org/wiki/LaserScope)
- [Marking of Toy, Look-Alike, and Imitation Firearms, Federal Register](https://www.federalregister.gov/documents/2023/05/11/2023-09999/marking-of-toy-look-alike-and-imitation-firearms) and [15 CFR Part 272, Cornell LII](https://www.law.cornell.edu/cfr/text/15/part-272)

**Game lists and regional releases**

- [Category:NES Zapper-compatible games, Wikipedia](https://en.wikipedia.org/wiki/Category:NES_Zapper-compatible_games)
- [NES Zapper / Light Gun Games List, gxrts.com](https://gxrts.com/nes/zapper) — includes the multicarts, which most lists skip
- [European NES Game List v0.10, 1998, NES HQ](http://www.neshq.com/lists/euneslist.txt) — the author says up front it's incomplete, so I only used it to corroborate
- [任天堂光線銃シリーズ以外の光線銃対応ファミコンソフト, 徒然ちょっとメモ](http://lesyn.com/nikki/2015/01/post-317.html) — Japanese third-party gun compatibility
- [『ガンサイト』1991年／ファミコン, レトロゲームの説明書保管庫](https://gamemanual.midnightmeattrain.com/entry/%E3%82%AC%E3%83%B3%E3%82%B5%E3%82%A4%E3%83%88)
- [Space Shadow, superfamicom.org](https://superfamicom.org/famicom/info/space-shadow)

**Individual game articles on Wikipedia** 
— [Duck Hunt](https://en.wikipedia.org/wiki/Duck_Hunt)
- [Hogan's Alley](https://en.wikipedia.org/wiki/Hogan%27s_Alley_(video_game))
- [Wild Gunman](https://en.wikipedia.org/wiki/Wild_Gunman)
- [Gumshoe](https://en.wikipedia.org/wiki/Gumshoe_(video_game))
- [Freedom Force](https://en.wikipedia.org/wiki/Freedom_Force_(1988_video_game)) 
- [Gotcha! The Sport!](https://en.wikipedia.org/wiki/Gotcha!_The_Sport!)
- [Shooting Range](https://en.wikipedia.org/wiki/Shooting_Range_(video_game))
- [Baby Boomer](https://en.wikipedia.org/wiki/Baby_Boomer_(video_game))
- [To the Earth](https://en.wikipedia.org/wiki/To_the_Earth)
- [Barker Bill's Trick Shooting](https://en.wikipedia.org/wiki/Barker_Bill%27s_Trick_Shooting) 
- [Operation Wolf](https://en.wikipedia.org/wiki/Operation_Wolf)
- [The Adventures of Bayou Billy](https://en.wikipedia.org/wiki/The_Adventures_of_Bayou_Billy)
- [Track & Field II](https://en.wikipedia.org/wiki/Track_%26_Field_II) 
- [Chiller](https://en.wikipedia.org/wiki/Chiller_(video_game))
- [Mechanized Attack](https://en.wikipedia.org/wiki/Mechanized_Attack)
- [Laser Invasion](https://en.wikipedia.org/wiki/Laser_Invasion)
- [The Lone Ranger](https://en.wikipedia.org/wiki/The_Lone_Ranger_(video_game))
- [Day Dreamin' Davey](https://en.wikipedia.org/wiki/Day_Dreamin%27_Davey)