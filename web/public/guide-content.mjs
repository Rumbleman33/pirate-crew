// Authored in-site guide explanations. Priorities are use-case upgrade recommendations, not simulation rankings.
// Evidence: recovered reference guides and build 34287→34521 public-resource comparison, checked 2026-11-02.
export const GUIDE_PRIORITY_NOTE = "These tiers rank upgrade priorities for a stated use case. They are not a universal item-strength or simulated win-rate ranking.";
export const GUIDE_CONTENT = {
  "pets": {
    "title": "Pets & skill stacking",
    "summary": "Choose skills for the problem your fighter actually has. Five equipped skills can operate independently; overlapping effects must be checked by buff ID, incoming overlay and group.",
    "sections": [
      {
        "id": "progression",
        "title": "Five separate pet benefits",
        "paragraphs": [
          "Pet stage stats, the pet book, collection groups, appearance and equipped combat skills are separate systems. Owning a pet does not mean its combat skill is selected, and wearing its appearance does not establish who owns its healing source in a fight. The captured catalog contains 75 pets.",
          "Typical individual-pet skill ranks unlock at stages 1, 3, 5, 7 and 9. Slot unlocks instead follow pet BOOK stages 1, 50, 100, 150 and 200. Check both tracks before paying for a fifth skill."
        ]
      },
      {
        "id": "activation",
        "title": "Why five skills do not dilute one random pool",
        "paragraphs": [
          "The recovered SkillComponent ticks actType 2 standalone skills independently of the ordinary action picker. These automatic pet skills are not five extra choices competing for the character’s next normal action. An actType 1 skill follows the action picker, so always check the actual activation mode.",
          "This rejects the old blanket advice to equip only one or two pet skills. Timing, valid targets, cooldowns and survival still constrain the value of a fifth slot. The original server’s battle-entry construction is needed to establish the exact owner and recipient mapping."
        ]
      },
      {
        "id": "stacking",
        "title": "Read the INCOMING buff, not just the stat name",
        "paragraphs": [
          "Stacking is a rule of the newly arriving buff. Different names are neither proof of stacking nor proof of replacement. Buff ID identifies an instance type; group is the key for overlay 2; class is used by some conditions and is a different field."
        ],
        "table": {
          "headers": [
            "Incoming overlay",
            "What happens",
            "Build consequence"
          ],
          "rows": [
            [
              "1",
              "Refresh/replace an existing copy of the same ID; other IDs remain",
              "Distinct IDs can coexist even in one group"
            ],
            [
              "2",
              "Remove every existing buff in the incoming buff’s group, then attach",
              "Last application wins; a weaker buff can erase a stronger one"
            ],
            [
              "3",
              "Add same-ID layers up to its tier, then refresh",
              "Tier 1 still permits only one layer"
            ]
          ]
        }
      },
      {
        "id": "examples",
        "title": "Concrete stacking and replacement cases",
        "paragraphs": [
          "Damage Up Goat, Lucky Serpent and Baby Nekomamushi use different overlay-1 IDs in group 3. Their +30, +40 and +60 percentage-point Damage Up contributions can coexist during overlapping uptime. They add to secDmgAdd; they are not three independent final-damage multipliers.",
          "Megalo’s +25-point Damage Reduction and Scrap Dog’s +35-point version use overlay 2 in group 5, so they replace one another rather than becoming +60. Fox and Vegapunk’s direct-evasion buffs likewise replace within group 9. Octopus’s brief Attack buff can clear the longer Straw Hat Attack buff in group 1 when its overlay-2 application arrives.",
          "Dugong, Fox and Vegapunk direct-crit buffs have distinct overlay-1 IDs in group 11 and can coexist until another effect clears the group. South Bird, Megalo, Captain Parrot and Halloween Karoo have distinct overlay-1 healing buffs in group 48; multiple IDs may heal together, while reapplying one ID refreshes it."
        ]
      },
      {
        "id": "healing",
        "title": "Healing: coefficient, interval and survival window",
        "paragraphs": [
          "At skill rank 5, South Bird heals for 15% of the buff source’s Attack every 500 ms, with a 6,100 ms lifetime and 30-second listed cooldown. Twelve nominal ticks imply 180% of source Attack before injury, death, removal or scheduling. The tooltip’s “per second” wording is misleading for this captured handler.",
          "Halloween Karoo’s rank-5 heal is 22.5% source Attack every 500 ms for 6,100 ms, nominally 45% per second, plus a harmful-buff-removal effect. Megalo’s rank-5 heal uses a 500 ms interval and 10,100 ms lifetime; its 67.5% coefficient is a configured source-Attack value, not a verified account-wide heal. A large theoretical total is worthless if the fighter dies before useful ticks."
        ]
      },
      {
        "id": "choices",
        "title": "Rank skills by the bottleneck they solve",
        "paragraphs": [
          "Use direct hit against misses, matching resistance against the incoming threat, and healing when there is enough time to recover. Lucky Serpent rank 5 adds 40 percentage points of Damage Up for 10 seconds. Its relative benefit depends on the existing attacker-minus-defender difference: moving a factor from 1 to 1.4 differs from moving 0.5 to 0.9.",
          "Nine-Tails Fox rank 5 supplies 15 percentage points each of direct crit, anti-crit, hit and evasion for 12 seconds. Those are direct chance terms, not rating bonuses. Halloween Ghost raises lifesteal amount, so it needs qualifying lifesteal procs; it does not supply their chance. A ranking that ignores these dependencies cannot choose the best five skills for every opponent."
        ]
      },
      {
        "id": "testing",
        "title": "Build a five-skill test instead of a universal myth",
        "paragraphs": [
          "Hold character level, stars, equipment and opponent fixed. First identify whether losses come from misses, burst, failed sustain or insufficient damage. Add one skill and compare several fights, recording application times, overwritten buffs, damage and healing. A single win does not isolate the cause.",
          "The recommendation tiers here organize upgrade decisions by use case. They are not a simulated leaderboard, and no current-build universal pet ranking is established by the recovered sources. The catalog supplies the exact rank, cooldown, payload and stack identity needed for a matchup-specific comparison."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Solve the deciding matchup failure",
        "reason": "Prioritize a compatible skill that directly fixes observed misses, early death or insufficient pressure."
      },
      {
        "tier": "A",
        "title": "Combine distinct-ID useful effects",
        "reason": "Separate overlay-1 healing or Damage Up IDs can provide complementary value when their uptime matters."
      },
      {
        "tier": "B",
        "title": "Use counters with a real target",
        "reason": "Anti-lifesteal, elemental resistance and cleanse earn their place when the opponent supplies that threat."
      },
      {
        "tier": "C",
        "title": "Delay redundant replacement effects",
        "reason": "Two group-replacing buffs can erase value; stage and collection purchases should have an explicit benefit."
      }
    ],
    "checklist": [
      "Unlock the intended slot through pet book stage, not individual pet stage.",
      "Read the selected rank’s actual stage requirement and numeric effects.",
      "Audit every incoming overlay-2 group for replacement.",
      "Separate source Attack, target selection, lifesteal chance and healing amount.",
      "Test all five skills with fixed opponent and loadout."
    ],
    "faq": [
      {
        "q": "Should I equip only one or two skills?",
        "a": "No. Standalone automatic pet skills tick independently. Select five useful, compatible skills when slots are available."
      },
      {
        "q": "Does the highest effect automatically win?",
        "a": "No. Overlay 2 follows application order, so a smaller incoming effect can remove a larger same-group effect."
      },
      {
        "q": "Can two healing pets stack?",
        "a": "Distinct overlay-1 buff IDs can coexist. Repeating the same ID refreshes instead of creating a second copy; actual recipients still need the battle-entry path."
      }
    ]
  },
  "mounts": {
    "title": "Mounts & reins",
    "summary": "Buy a useful stat or skill breakpoint for the fighter receiving it. Mount level, stars, collection rewards and reins are separate investments.",
    "sections": [
      {
        "id": "tracks",
        "title": "Separate the four investment tracks",
        "paragraphs": [
          "The recovered catalog contains 64 mounts. A mount can contribute level/star attributes, star-unlocked skills, collection rewards and reins progression. Compare each source separately; one large power increase does not reveal which track improved combat.",
          "A mount assigned elsewhere has an opportunity cost. Moving it to your main fighter can strengthen that fighter while weakening another member. Team modes require evaluating both changes."
        ]
      },
      {
        "id": "breakpoints",
        "title": "Stars buy specific breakpoints",
        "paragraphs": [
          "Common skill-unlock stars are 1, 3, 6 and 10, but the actual mount row controls. Read the current and target star rather than assuming a rarity label guarantees the same unlock schedule.",
          "Calculate the resources required to reach the next relevant breakpoint. A partial upgrade that stops immediately before a needed skill may be worse than finishing another mount’s usable threshold."
        ]
      },
      {
        "id": "example",
        "title": "Farul: distinguish ratings from damage",
        "paragraphs": [
          "Farul’s captured star skills illustrate why labels need decoding: star 1 grants HP +2,500; star 3 Anti-Crit rating +100; star 6 Hit rating +100; star 10 Crit rating bonus +7.5%. The last value is not critical damage.",
          "critPer scales Crit rating; critRate modifies the critical damage coefficient. A rating purchase depends on the opponent’s opposing rating and HP-related calculation. The same mount can therefore have different marginal value in different matchups."
        ]
      },
      {
        "id": "levels",
        "title": "Compare at the levels you will actually own",
        "paragraphs": [
          "Do not compare a fully developed mount against an entry-level alternative and attribute the entire gap to identity. Fix the obtainable level and stars, then compare the resulting useful stats and unlocked effects.",
          "For an upgrade, subtract the current row from the target row and include all intervening costs. Permanent HP may prevent an early death; Attack matters only if the fighter can reach and hit the target."
        ]
      },
      {
        "id": "collection",
        "title": "Collection rewards are group rewards",
        "paragraphs": [
          "MountBookGroup defines a reward for completing its listed group. Count it once when the group condition is met, not once per mount in that group. An individually weak mount can still be a sensible purchase if it cheaply completes a useful collection.",
          "Separate the immediate mount benefit from the collection benefit. This keeps a completion purchase from being mistaken for proof that the mount should be equipped on the main damage dealer."
        ]
      },
      {
        "id": "reins",
        "title": "Reins have their own thresholds and materials",
        "paragraphs": [
          "MountStage supplies the reins EXP thresholds, and MountStageItem defines material contributions. Reins progression is not the same operation as adding mount levels or stars.",
          "Before consuming materials, compare the remaining EXP to the next actual threshold and read that reward. Do not invent a universal level-to-stat conversion or assume surplus and overflow behavior without the current interface."
        ]
      },
      {
        "id": "plan",
        "title": "A practical upgrade comparison",
        "paragraphs": [
          "Write down the recipient, present mount, candidate mount, affordable development and next breakpoint. Then compare the fighter’s useful attributes, changed skills and collection completion after the purchase.",
          "Treat mounts that repair a tested weakness as higher priority than small score gains. Re-test with the same opponent after changing one track; movement and access to a target can matter more than the mount’s displayed power."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Finish a decisive breakpoint",
        "reason": "Reach a verified skill or survivability threshold on a fighter used in the target mode."
      },
      {
        "tier": "A",
        "title": "Complete an efficient collection",
        "reason": "A low marginal completion cost can grant a useful group reward once."
      },
      {
        "tier": "B",
        "title": "Develop a second role",
        "reason": "Invest when a second fighter or matchup needs the mount’s specific rating profile."
      },
      {
        "tier": "C",
        "title": "Delay score-only swaps",
        "reason": "Do not pay to replace a working mount without a measurable stat, skill or collection benefit."
      }
    ],
    "checklist": [
      "Confirm the recipient and the mount currently displaced.",
      "Use actual current/target level and star rows.",
      "Decode critPer versus critRate.",
      "Count collection rewards once.",
      "Price reins separately from mount level and stars."
    ],
    "faq": [
      {
        "q": "Is the rarest mount always best?",
        "a": "Rarity does not settle the actual developed stats, unlocked skill or opportunity cost for your roster."
      },
      {
        "q": "Does +7.5% Crit rating mean +7.5% critical damage?",
        "a": "No. They use separate attributes and affect different parts of combat."
      }
    ]
  },
  "treasures": {
    "title": "Treasures & recipient groups",
    "summary": "A treasure helps its configured recipient list. Compare current-star gains and usable material capacity before choosing the next upgrade.",
    "sections": [
      {
        "id": "identity",
        "title": "Treasures are not exclusive relics",
        "paragraphs": [
          "The captured treasure catalog contains 48 items. TreasureRef supplies the item and its explicit beneficiary-character list. Character-exclusive relics use a different system, different costs and skill-entry effects.",
          "Do not infer beneficiaries from the picture, lore relationship or item name. A treasure can be an excellent account investment while providing no benefit to the character you intend to improve."
        ]
      },
      {
        "id": "recipients",
        "title": "Read the full beneficiary list",
        "paragraphs": [
          "Cigar’s captured recipients are Gear 4 Luffy, Jinbe, X Drake, Garp, Sakazuki, Kaido and Big Mom. Its first-star row includes Attack +120, HP +1,200, Attack bonus +0.3% and HP bonus +0.3%. That is a defined list, not “everyone on the team.”",
          "The references do not establish that all listed characters must be deployed together. Owned-character counting in a power preview is not a hidden combat activation condition. Verify eligibility first and keep a UI power estimate separate from combat recipients."
        ]
      },
      {
        "id": "stars",
        "title": "Star rows describe the current total",
        "paragraphs": [
          "Use the target star’s attributes as its current configured value. Do not add every earlier star row to it. The gain from an upgrade is target minus current, plus any new material capacity you actually fill.",
          "A higher star may unlock headroom rather than deliver the whole potential benefit immediately. If the follow-up materials are unaffordable, compare the immediate benefit against other ready-to-use upgrades."
        ]
      },
      {
        "id": "materials",
        "title": "Materials convert into specific raw stats",
        "paragraphs": [
          "Treasure materials grant raw stats per unit: Attack +2, HP +20, Anti-Crit +2, Hit +2, Dodge +2 or Crit +2. They do not grant direct chance percentages. Current-star materialLimit determines the allowed capacity.",
          "Spend within the actual cap and recipient context. Hit can fix an accuracy deficit; Attack cannot compensate for every missed attack. A balanced material allocation is not automatically optimal for each character or opponent."
        ]
      },
      {
        "id": "marginal",
        "title": "Price both the star and its fill cost",
        "paragraphs": [
          "For a target star, include star-up currency, required copies and the resources needed to use its additional material limit. Compare the resulting stats on active beneficiaries rather than the headline capacity alone.",
          "When comparing treasures, count how many important characters really benefit and whether they are used in the mode being built for. Avoid multiplying a group reward by every owned unit in a single-fighter comparison."
        ]
      },
      {
        "id": "synergy",
        "title": "Use treasure stats to support the rest of the build",
        "paragraphs": [
          "Attack can improve Attack-scaled effects while HP buys time for healing and cooldowns. Crit/Anti-Crit and Hit/Dodge are opposed ratings, so their benefit changes with the matchup. The useful stat is the one affecting the loss condition.",
          "Percentage bonuses and raw materials should remain separate in your worksheet until the original stat aggregation basis is established. A +0.3% Attack bonus is not automatically +0.3% final damage."
        ]
      },
      {
        "id": "verify",
        "title": "Verify the recipient and the measured change",
        "paragraphs": [
          "Record the character sheet and loadout before and after a single treasure change. For combat, keep the opponent and other progression fixed; compare repeated hits or survival outcomes rather than only power.",
          "The catalog describes configured rows. Server activation, unlock requirements or presentation discrepancies should be recorded as observations instead of converted into undocumented rules."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Improve active recipients",
        "reason": "Choose a treasure whose beneficiary list includes the character or core group you actually use."
      },
      {
        "tier": "A",
        "title": "Buy affordable usable capacity",
        "reason": "A star upgrade is valuable when its stat increase and new material room can both be used."
      },
      {
        "tier": "B",
        "title": "Prepare a targeted secondary group",
        "reason": "Develop another list when that group has a concrete mode or matchup role."
      },
      {
        "tier": "C",
        "title": "Delay wrong-recipient spending",
        "reason": "An attractive item or high score is not a benefit to an ineligible fighter."
      }
    ],
    "checklist": [
      "Match exact character IDs/variants in the recipient list.",
      "Subtract current-star stats from target-star stats.",
      "Check materialLimit before buying filler.",
      "Include both star and material costs.",
      "Keep treasures separate from exclusive relics."
    ],
    "faq": [
      {
        "q": "Must every listed beneficiary be deployed?",
        "a": "The captured references do not establish that requirement. Do not infer it from a power preview."
      },
      {
        "q": "Do material stats stack over all old star rows?",
        "a": "No. Use the current star’s configured stats and capacity, not a sum of historical rows."
      }
    ]
  },
  "gems": {
    "title": "Gems & sockets",
    "summary": "Match gem stats to the missing part of the build. The recovered set has six gem types and nine levels, with important secondary-stat breakpoints.",
    "sections": [
      {
        "id": "catalog",
        "title": "The current gem set",
        "paragraphs": [
          "The captured GemRef contains 54 rows: six types with nine levels each. Older descriptions of eight types and seven levels do not match this set. Gem level and gem book stage are separate progression tracks."
        ],
        "table": {
          "headers": [
            "Level-1 gem",
            "Stat"
          ],
          "rows": [
            [
              "Ruby",
              "Attack +50"
            ],
            [
              "Emerald",
              "HP +500"
            ],
            [
              "Topaz",
              "Anti-Crit rating +20"
            ],
            [
              "Sapphire",
              "Crit rating +20"
            ],
            [
              "Amethyst",
              "Hit rating +20"
            ],
            [
              "Silver",
              "Dodge rating +20"
            ]
          ]
        }
      },
      {
        "id": "sockets",
        "title": "Slots are constrained by equipment and stars",
        "paragraphs": [
          "GemSlotRef has eight equipment-part groups with six slot rows each. The listed star requirements are 0, 2, 5, 8, 11 and 14, and gem-type eligibility is configured per row. Forty-eight configuration rows do not mean forty-eight interchangeable sockets are available at once.",
          "Inspect the actual equipment part, current stars and allowed gem type in the interface. A gem cannot solve the build if its intended socket is locked or ineligible."
        ]
      },
      {
        "id": "ruby",
        "title": "Ruby gains change character at later levels",
        "paragraphs": [
          "Ruby starts as flat Attack, then gains percentage and conditional stats. Compare the entire target row, not just the first Attack number. Level 8 adds PvP damage that applies in the actor-versus-actor branch of the ordinary calculator."
        ],
        "table": {
          "headers": [
            "Level",
            "Configured Ruby stats"
          ],
          "rows": [
            [
              "1–3",
              "Attack +50 / +100 / +200"
            ],
            [
              "4",
              "Attack +200; Attack bonus +2%"
            ],
            [
              "5",
              "Attack +300; Attack bonus +3%"
            ],
            [
              "6",
              "Attack +320; Attack bonus +3.2%; lifesteal chance +1.6%"
            ],
            [
              "7",
              "Attack +400; Attack bonus +4%; lifesteal chance +2%"
            ],
            [
              "8",
              "Attack +600; Attack bonus +4.5%; lifesteal chance +2.25%; PvP damage +2.25%"
            ],
            [
              "9",
              "Attack +800; Attack bonus +6%; lifesteal chance +3%; PvP damage +3%"
            ]
          ]
        }
      },
      {
        "id": "ratings",
        "title": "Ratings and direct chances are different purchases",
        "paragraphs": [
          "Sapphire Crit rating is opposed by Anti-Crit. Amethyst Hit rating is opposed by Dodge. Neither is a direct percentage chance, and rating bonuses are another separate operation. Opponent stats and HP affect the value of these raw-rating changes.",
          "A fighter already landing reliably may gain more from a different stat; a fighter missing decisive attacks may get little from a flat Attack upgrade. Diagnose the failure before treating a gem color as universally mandatory."
        ]
      },
      {
        "id": "sustain",
        "title": "Lifesteal chance needs a working healing route",
        "paragraphs": [
          "A Ruby’s later lifesteal chance is not its healing amount. The proc must occur on a qualifying event, and the resulting amount is affected by amount bonuses, their resistance and recipient healing reduction.",
          "This is why combining a chance source with Halloween Ghost can make mechanical sense, while Ghost alone does not establish any lifesteal proc chance. Still check uptime, damage dealt and whether burst kills the fighter before recovery."
        ]
      },
      {
        "id": "recipes",
        "title": "Use the actual combine recipe",
        "paragraphs": [
          "ItemCompound defines the captured conversion recipes. Do not assume every level uses the same number of lower gems, or that a random gem container guarantees the color you want. Check inputs, output type, quantity and any success field.",
          "Compare a merge’s net useful stats against keeping several lower gems in currently usable sockets. A higher-level gem is not automatically the better whole-loadout choice if merging empties valuable slots."
        ]
      },
      {
        "id": "book",
        "title": "Keep gem book and socket decisions separate",
        "paragraphs": [
          "GemBookStage is its own reward track. A book milestone can matter even when it does not change the gem currently worn, while a socket improvement can help without completing a book threshold.",
          "List the next book reward, the cost to reach it and the current socket alternative. Use guaranteed improvements for a spending plan; price random box outcomes separately until their eligible pools and draw rules are known."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Repair a decisive stat deficit",
        "reason": "Prioritize usable HP, Hit or damage stats according to the observed loss condition."
      },
      {
        "tier": "A",
        "title": "Reach a relevant secondary-stat breakpoint",
        "reason": "For example, Ruby’s later lifesteal chance or PvP damage can add a new function in the right mode."
      },
      {
        "tier": "B",
        "title": "Complete an efficient book threshold",
        "reason": "Choose it when the actual milestone reward beats the socket alternative."
      },
      {
        "tier": "C",
        "title": "Delay blind merging",
        "reason": "Do not sacrifice several productive sockets solely for one higher-level label."
      }
    ],
    "checklist": [
      "Check part, star gate and allowed type before buying.",
      "Use the entire target-level stat row.",
      "Keep ratings, direct chance and percentage bonuses separate.",
      "Check the exact combine recipe.",
      "Compare the whole socket layout before consuming gems."
    ],
    "faq": [
      {
        "q": "Are there eight gem types?",
        "a": "The recovered current set has six types, nine levels and 54 rows."
      },
      {
        "q": "Is level 4 Ruby just a larger flat Attack gem?",
        "a": "No. It keeps +200 Attack and adds +2% Attack bonus; later levels add further distinct stats."
      }
    ]
  },
  "gear": {
    "title": "Gear, sets & forging",
    "summary": "Compare complete legal loadouts. Useful set thresholds and actual affixes matter more than a single piece’s quality label or power.",
    "sections": [
      {
        "id": "eligibility",
        "title": "Start with legal equipment",
        "paragraphs": [
          "The recovered catalog contains 1,950 gear definitions across eight equipment-part codes. Each item can specify character/class eligibility, required level, step, quality, stars, base attributes, random-affix settings and set membership.",
          "An item is not an upgrade if the intended character cannot equip it. Establish the exact character variant, slot and current requirements before spending on a forge or compound path."
        ]
      },
      {
        "id": "affixes",
        "title": "Random-affix pools are not guaranteed stat bundles",
        "paragraphs": [
          "randomAttrIndex links an item to an eligible affix pool, and randomAttrNum controls its number of affixes. A catalog listing multiple possible affixes is not a promise the item receives all of them.",
          "Weights describe choices within the appropriate pool. Multiple-affix results may depend on duplicate or exclusion rules, so multiplying simple single-affix shares can overstate the chance of a perfect item."
        ]
      },
      {
        "id": "sets",
        "title": "Evaluate 3-, 6- and 8-piece thresholds",
        "paragraphs": [
          "Captured equipment sets grant threshold effects at 3, 6 and 8 pieces. Replacing one piece can lose a threshold; equipping a lower-scoring piece can complete one. Compare the resulting entire outfit.",
          "A useful set effect, enough Hit to connect, or HP to survive the opening can outweigh a larger displayed Attack or power value on the candidate item. Keep equipment sets distinct from the separate character aura/suit system."
        ]
      },
      {
        "id": "forge",
        "title": "Forging contains multiple different probability layers",
        "paragraphs": [
          "EquipWorkshopLevelRef establishes workshop requirements; EquipWorkshopCostRef supplies costs; EquipWorkshopOrderRef supplies weighted outcomes. ProShow is a displayed-quality weighting path, while lucky-score configuration describes a separate guarantee schedule.",
          "Do not divide a candidate weight by a displayed quality denominator or combine lucky rewards with ordinary draws as if they were one pool. The server’s full orchestration is not recovered, so report conditional shares with their assumptions."
        ]
      },
      {
        "id": "compound",
        "title": "Compounding fields use different units",
        "paragraphs": [
          "A captured EquipCompound successRate of 6,000 on its 10,000 scale means 60%; addRate 1,000 is ten percentage points. That does not establish the full server failure or pity transition.",
          "EquipSuitCompound uses fields such as baseSuccess 80 and failAddSuccess 10 on a different scale. Dividing all “success” fields by 10,000 creates false odds. Read the actual table family and do not assume failure consumes or preserves a particular item without the live rule."
        ]
      },
      {
        "id": "recycling",
        "title": "Dismantling is not a universal refund",
        "paragraphs": [
          "Exchange and dismantle rewards follow their exact recipes. Do not value an unwanted item as fully recoverable unless its configured conversion and the current interface actually support that recovery.",
          "Before a destructive operation, record the inputs, outputs, locked/equipped status and whether the item completes a set. A future upgrade may need the current piece even if its individual stats are unimpressive."
        ]
      },
      {
        "id": "decision",
        "title": "Compare the affordable finished outfit",
        "paragraphs": [
          "For each candidate, include creation cost, necessary star/step progression, likely affix quality and the set threshold gained or lost. Separate a guaranteed base upgrade from the speculative value of a rare roll.",
          "Test complete outfits with fixed character and opponent. If the outcome changes, inspect landed hits, early deaths, set uptime and skill access so the improvement has an identified cause rather than only a score increase."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Keep a functional legal loadout",
        "reason": "Meet survival and accuracy needs and preserve useful set thresholds."
      },
      {
        "tier": "A",
        "title": "Finish a set or strong affordable piece",
        "reason": "Choose a known base/stat breakpoint over an unpriced perfect-affix assumption."
      },
      {
        "tier": "B",
        "title": "Roll targeted affixes after basics work",
        "reason": "Use the correct eligible pool and a clear stop budget."
      },
      {
        "tier": "C",
        "title": "Delay score-only set breaks",
        "reason": "Higher quality is not enough justification to lose a valuable whole-loadout effect."
      }
    ],
    "checklist": [
      "Confirm class, level, part and step eligibility.",
      "Compare the full outfit at 3/6/8-piece thresholds.",
      "Distinguish possible affixes from rolled affixes.",
      "Check probability units per table family.",
      "Read exact dismantle and compound outputs before consuming."
    ],
    "faq": [
      {
        "q": "Does the item get every listed random attribute?",
        "a": "No. The pool lists possible outcomes; randomAttrNum limits the number rolled."
      },
      {
        "q": "Is 80 in every success field 0.8%?",
        "a": "No. Table families use different units; EquipSuitCompound and EquipCompound must be read separately."
      }
    ]
  },
  "ships": {
    "title": "Ships, cabins & fleet support",
    "summary": "Ships combine explicit recipient stats with separate dock, cabin, chart and cooking systems. Read each track before treating a ship upgrade as a team-wide damage multiplier.",
    "sections": [
      {
        "id": "recipients",
        "title": "Ship recipients are explicit",
        "paragraphs": [
          "The recovered ship catalog contains 22 ships. ShipsRef supplies the characters eligible for a ship’s configured benefit. The artwork and story association do not replace that list.",
          "Choose a ship for characters used in the target mode, then compare development and opportunity cost. Do not multiply its stats by every character owned or assume every deployed fighter qualifies."
        ]
      },
      {
        "id": "stars",
        "title": "Stars and materials share a capacity decision",
        "paragraphs": [
          "A ship’s star row describes its current configured stats, not a reward to add repeatedly for every previous star. Its material limit controls how much further development can be applied.",
          "Per-unit ship materials grant HP +100 from Nails, Attack +10 from Paint, Hit rating +16 from Gear and Anti-Crit rating +16 from Steel. They are raw stats, not direct chance percentages. Price the star and the cost of filling its new room together."
        ]
      },
      {
        "id": "dock",
        "title": "Dock level is its own stat row",
        "paragraphs": [
          "Use the dock’s current-level attributes. Summing all historical dock rows would count the same progression repeatedly. Compare the next row minus the current row for the incremental benefit.",
          "Keep dock costs and beneficiaries separate from a ship’s personal star progression. A shared-system improvement and a one-recipient improvement should not be compared using unrelated power totals."
        ]
      },
      {
        "id": "cabins",
        "title": "Cabins have several development fields",
        "paragraphs": [
          "Cabin configuration separates level, stage, star, costs, attributes and hpRate/atkRate. ShipRoom includes cabin-level thresholds at 50, 100, 150, 200, 250 and 300 with rate values of 1,000.",
          "The original server’s full stat basis is not established here. A listed rate of 1,000 must not be advertised as a guaranteed 10% final team damage increase. Follow the actual attribute and eligible base."
        ]
      },
      {
        "id": "charts",
        "title": "Chart stars and group thresholds are distinct",
        "paragraphs": [
          "A chart’s individual star stats and its group’s needStar threshold are separate rewards. Count a group reward once when its condition is met. Do not add the same collection benefit to every chart.",
          "A small purchase that finishes a useful group may beat a larger individual-star upgrade. Compare the full cost to the threshold and the reward you can activate now, not an eventual maximum."
        ]
      },
      {
        "id": "cooking",
        "title": "Food is a timed resource, not permanent progression",
        "paragraphs": [
          "Recipes define ingredients, output, unlock conditions, group and preparation time. Cooking slots have their own requirements. Read LimitAttr duration and recipient conditions before using food in a comparison.",
          "A temporary food buff can explain a stronger fight without any permanent build improvement. Tournament or controlled tests must fix food, duration and remaining uptime for both sides."
        ]
      },
      {
        "id": "content",
        "title": "Ship content restrictions affect usable value",
        "paragraphs": [
          "Ship challenges can restrict character type or attack type. Read the mode’s actual eligibility before building around a favorite team. Configured reward payloads describe awards; they are not automatically drop chances.",
          "When planning upgrades, separate guaranteed content access from potential rewards and conditional rolls. Check current displayed rewards against actual received rewards, particularly after public-resource changes."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Support eligible active fighters",
        "reason": "Prioritize the ship and track that improve the characters used in the intended mode."
      },
      {
        "tier": "A",
        "title": "Finish affordable cabin or chart thresholds",
        "reason": "Use actual rewards and prerequisites rather than assuming every rate is final team damage."
      },
      {
        "tier": "B",
        "title": "Prepare food for a defined attempt",
        "reason": "Timed bonuses are useful when their duration, recipients and cost fit the attempt."
      },
      {
        "tier": "C",
        "title": "Delay ineligible or speculative upgrades",
        "reason": "A ship cannot help a character outside its recipient rules merely because its power is high."
      }
    ],
    "checklist": [
      "Verify the recipient list and content restrictions.",
      "Use current star/dock rows rather than summed history.",
      "Include material capacity and fill costs.",
      "Count chart group rewards once.",
      "Normalize food during tests."
    ],
    "faq": [
      {
        "q": "Does cabin rate 1,000 guarantee 10% more final damage?",
        "a": "No. The stat base and aggregation are not established by that rate field alone."
      },
      {
        "q": "Are Nails and Paint percentage bonuses?",
        "a": "No. Their captured per-unit gains are raw HP +100 and raw Attack +10 respectively."
      }
    ]
  },
  "posters": {
    "title": "Posters & bounty progression",
    "summary": "A poster portrait identifies an entry, while its category identifies beneficiaries. Upgrade the group your roster uses and compare level deltas.",
    "sections": [
      {
        "id": "system",
        "title": "Poster progression is PirateReport",
        "paragraphs": [
          "The captured poster system uses PirateReport references. Its portrait and recipient category are different concepts. A Mihawk portrait can represent a Warlords-category benefit rather than a Mihawk-only benefit.",
          "Read the category before evaluating the item. A visually attractive poster can be irrelevant to the fighter you are developing; an ordinary-looking entry can serve an entire core group."
        ]
      },
      {
        "id": "categories",
        "title": "Recipient categories use exact character variants",
        "paragraphs": [
          "The captured categories include Warlords, Emperors, Navy, Supernovas, Straw Hats, Emperor commanders and a separate high-end group. Their configured membership is not an invitation to add every lore-related character."
        ],
        "table": {
          "headers": [
            "Category",
            "Captured examples / membership"
          ],
          "rows": [
            [
              "Warlords",
              "Mihawk, Kuma, Boa, Crocodile, Moria, Doflamingo, Jinbe"
            ],
            [
              "Emperors",
              "Whitebeard, Shanks, Nika, Kaido, Big Mom, Buggy"
            ],
            [
              "Navy",
              "Sengoku, Garp, Sakazuki, Kuzan, Borsalino, Smoker, Helmeppo, Koby"
            ],
            [
              "Supernovas",
              "Law, Kid, Killer, Urouge, X Drake, Apoo, Bege, Bonney, Hawkins"
            ],
            [
              "Straw Hats",
              "Luffy, Gear 2 Luffy, Gear 4 Luffy, Zoro, Sanji, Usopp, Nami, Robin, Chopper, Franky, Brook, Vivi"
            ],
            [
              "Emperor commanders",
              "Marco, Benn Beckman, Wano Zoro"
            ],
            [
              "High-end group",
              "Yasopp, Ace, Vista, Jozu, Bellamy, Masked Sanji"
            ]
          ]
        }
      },
      {
        "id": "variants",
        "title": "Names do not make variants interchangeable",
        "paragraphs": [
          "The Straw Hats category explicitly includes Luffy, Gear 2 Luffy and Gear 4 Luffy alongside the listed crew entries. Nika appears in the Emperors list. These separate records are why matching exact variants matters.",
          "Navy and Supernova category membership is likewise configured. If the roster changes to a different character variant, re-check the poster category instead of carrying over the old assumption."
        ]
      },
      {
        "id": "levels",
        "title": "A level row is the current value",
        "paragraphs": [
          "Poster 101’s first row is a Mihawk portrait in the Warlords category with Attack +10 and zero HP, Crit and Dodge in that row. Higher rows must be read directly; do not assume an identical increment everywhere.",
          "The upgrade gain is next-level minus current-level attributes. Adding all earlier rows would double-count current progression. Compare that delta on active eligible characters."
        ]
      },
      {
        "id": "links",
        "title": "Progression links are not complete server unlock rules",
        "paragraphs": [
          "typeUpperRefId and nextRefId connect entries or progression steps. They help follow the table, but they do not prove the complete live server unlock condition.",
          "Before buying a prerequisite chain, confirm the interface’s current lock, cost and next reward. Do not infer player level, event access or a free reward from a reference link alone."
        ]
      },
      {
        "id": "value",
        "title": "Count useful beneficiaries, not owned portraits",
        "paragraphs": [
          "A group reward can be efficient when several active fighters qualify. In a 1v1 build, only the selected character’s eligibility matters. Counting unused characters exaggerates the combat return.",
          "Compare the next poster improvement with other guaranteed stat sources. If the fighter misses or dies early, a relevant rating or HP gain may be more useful than a larger unrelated Attack preview."
        ]
      },
      {
        "id": "test",
        "title": "Verify the changed category in isolation",
        "paragraphs": [
          "Record the selected character and poster level, change only the poster progression, and compare the character sheet or repeated combat outcomes. Include another nonrecipient as a control when testing category behavior.",
          "Treat a UI discrepancy as a specific unresolved recipient or display issue. It is not proof that every poster or the entire system is inactive."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Improve the category of your active core",
        "reason": "Choose exact configured recipients in the target mode."
      },
      {
        "tier": "A",
        "title": "Buy efficient next-level stat deltas",
        "reason": "Compare the real next reward and cost rather than historical row totals."
      },
      {
        "tier": "B",
        "title": "Develop a future group with a roster plan",
        "reason": "A secondary category is reasonable when its characters will actually be used."
      },
      {
        "tier": "C",
        "title": "Delay portrait-driven spending",
        "reason": "The face on the poster is not a reliable guide to who benefits."
      }
    ],
    "checklist": [
      "Match the character variant to category membership.",
      "Read current and next level rows.",
      "Check actual interface locks and costs.",
      "Count only useful eligible fighters.",
      "Keep poster category and portrait separate."
    ],
    "faq": [
      {
        "q": "Does a Mihawk poster benefit only Mihawk?",
        "a": "Not necessarily. The captured entry belongs to the Warlords category, whose configured recipient list is broader."
      },
      {
        "q": "Should I add every previous poster-level row?",
        "a": "No. Use the current row and calculate the target-minus-current improvement."
      }
    ]
  },
  "skins": {
    "title": "Skins & skill entries",
    "summary": "Separate appearance, star stats and real skill modifications. A skin can change combat mechanics, but the entry and current star determine what it actually changes.",
    "sections": [
      {
        "id": "tracks",
        "title": "Character skins and skill skins are separate",
        "paragraphs": [
          "The recovered catalog contains 110 character skins with five star rows. GeneralSkinRef links a skin to its character, activation cost, quality, display behavior and optional skill entry. GeneralSkillSkinRef is a separate skill-skin system.",
          "A visual effect is not evidence of a damage bonus. First identify whether the purchase changes appearance, attributes, a mechanical entry or some combination."
        ]
      },
      {
        "id": "costs",
        "title": "Activation and star-up costs point in different places",
        "paragraphs": [
          "Activation cost belongs to GeneralSkinRef. Once active, the CURRENT GeneralSkinStar row provides the next upgrade cost. Do not read the target row as the price to enter it.",
          "A common captured sequence consumes 1 + 2 + 3 + 4 + 5 = 15 copies from unowned to five stars, but confirm the actual item’s rows rather than applying that total universally."
        ]
      },
      {
        "id": "stats",
        "title": "Current-star stats are not cumulative history",
        "paragraphs": [
          "Moon Rabbit Nika illustrates the scale: its five rows list Attack/HP bonuses of 30%, 60%, 90%, 120% and 150%. Five stars means the current 150% row, not the sum of all five rows.",
          "An Attack percentage does not directly equal the same percentage final-damage improvement. The eligible stat base, existing bonuses, hit outcomes and later damage factors all matter."
        ]
      },
      {
        "id": "entries",
        "title": "Trace the skin entry to its real effect",
        "paragraphs": [
          "Skill entries can add skills or effects, replace buffs or projectiles, alter cooldowns or coefficients, or change visuals. Read the affected skill and condition instead of summarizing every entry as “more damage.”",
          "SkillEntryDamage modifies the coefficient of its affected skill. It is not a global final multiplier for every attack or every damage-over-time tick. A cooldown change helps only when the skill can actually be selected and used."
        ]
      },
      {
        "id": "appearance",
        "title": "Visual replacement is a legitimate separate benefit",
        "paragraphs": [
          "Halloween King’s captured type-10 entry is a visual replacement; that fact alone supplies no damage increase. An owner may still value the appearance, but a combat-priority ranking must not invent a hidden mechanical return.",
          "Owned skins, their stars and the worn skin ID are distinct state. Their existence does not prove every owned skin’s stats stack on the original server. Test that ownership path explicitly if it changes a purchase decision."
        ]
      },
      {
        "id": "compatibility",
        "title": "Check entries against other character upgrades",
        "paragraphs": [
          "Potential, relics and skins can all reference skills or buff replacements. Two upgrades that touch the same effect may not produce the simple sum suggested by their descriptions.",
          "Read the actual active entry chain and verify which skill/buff reaches combat. Earlier recovered-client duration-extension and conditional-final-damage observations are path-specific caveats, not permission to label every skin or character broken."
        ]
      },
      {
        "id": "spending",
        "title": "Buy the benefit you intend to use",
        "paragraphs": [
          "Prioritize a skin for an active character when its real mechanical entry or stat gain justifies the price. Compare activation with the next star and with other progression tracks; neither rarity nor visual complexity settles that comparison.",
          "For a live test, hold all other progression fixed and compare ownership, selected appearance and star level one at a time. Record the current build and distinguish a visual change from damage, cooldown or buff behavior."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Useful mechanics on an active character",
        "reason": "A verified skill-entry change that solves a real combat issue can justify early investment."
      },
      {
        "tier": "A",
        "title": "Efficient current-star stats",
        "reason": "Compare the actual incremental stats and next-star cost."
      },
      {
        "tier": "B",
        "title": "Appearance you specifically want",
        "reason": "Treat cosmetic value as its own purchase decision."
      },
      {
        "tier": "C",
        "title": "Delay assumed global multipliers",
        "reason": "Do not buy from a visual replacement or coefficient description interpreted as universal final damage."
      }
    ],
    "checklist": [
      "Distinguish character skin from skill skin.",
      "Read activation and current-row next-star costs correctly.",
      "Use current-star totals, not accumulated historical rows.",
      "Trace the exact affected skill and entry type.",
      "Verify ownership versus worn-appearance behavior when relevant."
    ],
    "faq": [
      {
        "q": "Does five-star Moon Rabbit mean 450% from adding the rows?",
        "a": "No. The captured five-star row is 150% Attack/HP bonus; old rows are not added again."
      },
      {
        "q": "Do all skins add a damage ability?",
        "a": "No. Some entries only replace visuals; others change a specific mechanical effect."
      }
    ]
  },
  "relics": {
    "title": "Exclusive relics & effect verification",
    "summary": "Exclusive relics belong to particular characters and modify specific effects. Read every level individually, especially conditional bonuses with unresolved live behavior.",
    "sections": [
      {
        "id": "identity",
        "title": "Exclusive relics are not treasures",
        "paragraphs": [
          "The recovered exclusive system has 25 items, each tied to one character and five levels. UniqueRef and UniqueLvRef define this track; TreasureRef defines the separate group-benefit system.",
          "A relic’s character restriction is fundamental. Its strongest-looking level is irrelevant to another character, and a working earlier effect is not invalid merely because a later effect has a caveat."
        ]
      },
      {
        "id": "costs",
        "title": "Read activation and next-level costs correctly",
        "paragraphs": [
          "At inactive level 0, use UniqueRef’s activation cost. Once active, the current UniqueLvRef row supplies the next upgrade cost. The common five-level copy sequence totals 15 copies from unowned, but the actual rows decide.",
          "Price the target effect by the entire path needed to reach it. A valuable level-5 effect may be a poor immediate purchase if the intervening cost prevents more useful guaranteed upgrades."
        ]
      },
      {
        "id": "chain",
        "title": "Follow level → entry → skill → effect",
        "paragraphs": [
          "A useful relic explanation identifies which skill changes, the trigger, the condition, the target, any internal cooldown, and the linked buff or handler. Descriptive wording alone cannot establish the executed result.",
          "For conditional damage, confirm the actual condition identity. An airborne-looking animation is not automatically class 63, and a note mark is a separate class. A condition can fail even if the effect looks visually appropriate."
        ]
      },
      {
        "id": "modifier-caveat",
        "title": "Recovered-client conditional damage caveat",
        "paragraphs": [
          "An isolated reproduction in the recovered client found a type-27 OnCalc handler changing context.damage while the ordinary calculator consumes modify4. The unchanged returned hit in that reproduction is evidence about that client path, not a fresh live-server test.",
          "The November 2 comparison to public build 34521 found the handler and calculator behavior unchanged. This neither confirms a live defect nor rules out a server-side fix. Do not sell those listed conditional bonuses as verified live damage until tested."
        ]
      },
      {
        "id": "scope",
        "title": "An affected level does not invalidate the full item",
        "paragraphs": [
          "Affected reference paths include some exclusive levels for Nika, Wano Zoro, Masked Sanji, Rayleigh, Shiki, Uta and other characters. The scope is the specific linked effect; another level may provide a different, working benefit.",
          "Likewise, poor old rankings are not software-bug evidence. Evaluate the relic’s working stats, control, buffs or other changes separately from the unresolved conditional multiplier."
        ]
      },
      {
        "id": "duration-caveat",
        "title": "Duration changes need measured timings",
        "paragraphs": [
          "Another recovered-client reproduction found a duration extension counted twice: a base three-second buff with a one-second extension expired at five seconds in that isolated path instead of four. Exposure depends on the active entry and buff route.",
          "Do not silently convert that result into an advertised live duration for every relic or potential node. Record application/removal timing with and without only the relevant entry."
        ]
      },
      {
        "id": "testing",
        "title": "Verify a relic with a controlled comparison",
        "paragraphs": [
          "For a conditional bonus, fix attacker, defender, skill rank, other buffs and loadout. Compare many landed, noncritical, unblocked hits with and without the qualifying condition or relic level. The ordinary calculator’s random factor ranges from 0.8 to 1.2, so one hit cannot settle a modest bonus.",
          "Publish the build, mode and isolated effect tested. An improvement elsewhere in the kit does not prove the conditional handler was fixed, and a client-file comparison alone does not prove server behavior."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Verified useful effects on your active character",
        "reason": "Prioritize a clear working benefit under conditions your build can actually create."
      },
      {
        "tier": "A",
        "title": "Affordable next-level breakpoints",
        "reason": "Evaluate the next effect independently, including the entire cost to reach it."
      },
      {
        "tier": "B",
        "title": "Conditional effects awaiting a clean test",
        "reason": "Keep their promised value separate from already established benefits."
      },
      {
        "tier": "C",
        "title": "Delay wrong-character or assumed bonuses",
        "reason": "An impressive tooltip is insufficient when the recipient or live mechanism is unresolved."
      }
    ],
    "checklist": [
      "Match the exclusive to the exact character.",
      "Use the current level’s next-upgrade cost.",
      "Trace entry, trigger, condition and handler.",
      "Separate recovered-client observations from live confirmation.",
      "Test one effect at a time over repeated comparable hits."
    ],
    "faq": [
      {
        "q": "Are all relic bonuses broken?",
        "a": "No. The recovered issue concerns specific conditional-final-damage paths. Other effects and levels require their own evaluation."
      },
      {
        "q": "Did build 34521 prove the issue was fixed?",
        "a": "No visible public-client fix was found. Private server behavior was not established by that comparison."
      }
    ]
  },
  "damage": {
    "title": "Stats & the damage engine",
    "summary": "Decode the actual attribute before comparing bonuses. Ratings, direct chances, damage factors and recovery coefficients are different mechanisms.",
    "sections": [
      {
        "id": "units",
        "title": "Start with units and percentage points",
        "paragraphs": [
          "Many percentage fields use 10,000 = 100%, but raw Attack, HP, Crit, Anti-Crit, Hit and Dodge remain numeric ratings. A 1,000 value in a percent field means 10%; the same number in a raw rating field does not.",
          "Increasing chance from 20% to 30% is +10 percentage points and a 50% relative increase. Increasing a rating by 10% is another operation. Keep these quantities named separately."
        ]
      },
      {
        "id": "ratings",
        "title": "Ratings oppose other ratings",
        "paragraphs": [
          "Crit is compared with Anti-Crit, and Hit with Dodge. In the recovered ordinary calculator, these comparisons can affect landed-hit base damage as well as crit/miss chances, with HP appearing in rating comparisons.",
          "Direct secCrit/secAntCrit and secHit/secDodge are separate chance terms. critPer is a bonus to Crit rating; critRate changes critical damage. An icon that says “Crit” is insufficient to identify the operation."
        ]
      },
      {
        "id": "factors",
        "title": "Damage bonuses occupy different factors",
        "paragraphs": [
          "General damage uses a ratio: an attacker numerator containing 1 + extDmgPer plus qualifying PvP damage, divided by a defender denominator containing 1 + deDmgPer plus qualifying PvP reduction. +20% general reduction alone gives 1/1.2 damage, about 16.7% less.",
          "Damage Up and Damage Reduction use the separate factor max(1 + attacker secDmgAdd − defender secDmgSub, 0). Bonuses inside a factor add or subtract there; distinct factors multiply. Equal tooltip percentages are not necessarily equal final gains."
        ]
      },
      {
        "id": "critical-block",
        "title": "Crit damage and block strength have their own bases",
        "paragraphs": [
          "The captured default critical multiplier is 1.5, modified by critRate and antCritRate with a minimum of 1.2. That is distinct from the chance to crit.",
          "A successful default block divides damage by 1.5. block and antBlock influence its chance, while blockRate and antBlockRate change the divisor. More block strength does not create more successful blocks by itself."
        ]
      },
      {
        "id": "elements",
        "title": "Resistance and armor break need exact payloads",
        "paragraphs": [
          "The captured elemental-resistance stats are flat matching-element subtractions at the adjusted-base-attack stage. Fire resistance is not universal damage reduction and should not be priced as such.",
          "Armor Break often supplies negative secDmgSub. The ordinary calculator has no universal Armor/Defense subtraction that every armor-break label reduces. Read the buff’s duration, overlay, group and class to establish the real operation."
        ]
      },
      {
        "id": "recovery",
        "title": "Lifesteal amount is not lifesteal chance",
        "paragraphs": [
          "leech minus antLeech determines the relevant proc-chance term. The amount coefficient starts at 0.5, changes with leechRate and antLeechRate, and has a minimum of 0.1 in the captured path. A large amount bonus cannot substitute for a qualifying proc.",
          "Injury is recipient-side healing reduction in addHp: in the ordinary range, incoming heal is multiplied by 1 − injury. Shields are separate buffers, often sized from source Attack; an HP heal and an Attack-scaled heal use different bases."
        ]
      },
      {
        "id": "timing",
        "title": "Speed and coefficients do not guarantee the first hit",
        "paragraphs": [
          "Movement speed is not attack interval, listed cast time or cooldown. Range, movement, the selected action, animation/effect timing, projectile travel and target validity can decide when a ready move actually lands.",
          "A coefficient multiplies its specified offensive basis before later factors. A 200% coefficient is not a guarantee of twice every opponent’s damage, nor evidence that the move hits first. Timing references are not measured attacks-per-minute rankings."
        ]
      },
      {
        "id": "expected",
        "title": "Compare expected useful output",
        "paragraphs": [
          "Expected damage includes misses, crits, blocks, conditional uptime and time alive. The ordinary random factor spans 0.8–1.2, so one spectacular critical hit is weak evidence about sustained performance.",
          "Displayed power is an accounting field, not a multiplier in ordinary damage. A useful build comparison fixes the opponent and changes one mechanism, then checks repeated hits, survival and actual useful actions."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Identify the controlling mechanism",
        "reason": "Resolve whether the loss comes from hit rate, survival, damage factor or access to the target."
      },
      {
        "tier": "A",
        "title": "Improve the relevant independent factor",
        "reason": "Compare actual marginal gains rather than matching tooltip percentages."
      },
      {
        "tier": "B",
        "title": "Add conditional output with reliable uptime",
        "reason": "Use crit, lifesteal or mode-specific bonuses when their prerequisites are present."
      },
      {
        "tier": "C",
        "title": "Ignore score-only conclusions",
        "reason": "Power and isolated high hits are insufficient evidence of a stronger combat build."
      }
    ],
    "checklist": [
      "Read raw attribute name and units.",
      "Separate rating, direct chance and damage coefficient.",
      "Apply PvP terms only in the qualifying branch.",
      "Fix opponent and other buffs during comparison.",
      "Use repeated comparable hits and useful uptime."
    ],
    "faq": [
      {
        "q": "Does +40% Damage Up always mean 40% more final damage?",
        "a": "No. It adds 40 percentage points inside its difference factor; the relative gain depends on existing bonuses and reduction."
      },
      {
        "q": "Is movement speed attack speed?",
        "a": "No. Movement, attack interval, cast/effect timing and cooldown are distinct fields."
      }
    ]
  },
  "control": {
    "title": "Control, statuses & stacking",
    "summary": "A status has a name, state, buff ID, group and class. Use the exact identity a condition checks, then account for incoming replacement rules.",
    "sections": [
      {
        "id": "identity",
        "title": "Five status identities answer different questions",
        "paragraphs": [
          "The visible name describes presentation; state flags influence actor behavior; buff ID identifies a specific effect; group controls overlay-2 replacement; class is used by some conditions. Equal-looking effects can differ mechanically.",
          "The handler named CdtBuffGroup actually queries same-class buffs in this recovered client. Do not infer a condition’s target identity from the handler’s English name alone."
        ]
      },
      {
        "id": "hard-control",
        "title": "Hard control and movement restraint differ",
        "paragraphs": [
          "Stun, paralysis, freeze and airborne are distinct actor states. Root/imprison is movement restraint and does not automatically prove all attacks or casting stop. Slow usually changes movement speed, not the attack interval or cooldown.",
          "Super Armor is a distinct control-resistance state, not ordinary damage immunity. To determine whether a move is interrupted, follow the actual action/state path or isolate it in a live test."
        ]
      },
      {
        "id": "silence",
        "title": "Silence and disarm labels need verification",
        "paragraphs": [
          "The recovered ordinary picker checks Silent on common skills and Disarm on the non-common bucket. That is counterintuitive relative to common game terminology. Additional state gates and server behavior may matter.",
          "A meaningful test records normal attacks and special skills separately under each status. Do not publish another game’s assumed silence/disarm definitions as established behavior here."
        ]
      },
      {
        "id": "conditions",
        "title": "Airborne class 63 is not note class 64",
        "paragraphs": [
          "Buff state 20 maps to Floating. Relevant airborne buffs use class 63, and a condition such as 1_63 checks that class. An airborne-looking animation alone is not enough.",
          "Uta’s note mark uses class 64. She can apply airborne separately, but that does not repair Shiki’s recovered-client conditional-final-damage field mismatch. Mark application, condition recognition and bonus damage are three separate questions."
        ]
      },
      {
        "id": "overlay",
        "title": "Incoming overlay determines coexistence",
        "paragraphs": [
          "Overlay 1 refreshes the same buff ID and leaves other IDs alone. Overlay 2 clears the incoming buff’s group before attaching, so order matters. Overlay 3 adds same-ID layers up to tier, then refreshes; tier 1 prevents multilayer accumulation.",
          "Do not compress these into “same type never stacks.” Two group-matched overlay-1 IDs can coexist until an overlay-2 buff arrives and clears them. Class-matched effects need not share a replacement group."
        ]
      },
      {
        "id": "dots",
        "title": "Damage over time depends on exact ticks",
        "paragraphs": [
          "Bleed, burn and poison are labels; BuffRef supplies the actual coefficient, element, interval, lifetime and layering. A poison-looking effect is not automatically recognized by every poison passive.",
          "Milliseconds matter. A 2,100 ms lifetime with a 1,000 ms interval can allow two nominal ticks; rounding it to “two seconds” can obscure scheduling boundaries. Duration-extension observations from the recovered client are not measured live durations."
        ]
      },
      {
        "id": "protection",
        "title": "Cleanse, invincibility and shields are separate",
        "paragraphs": [
          "A cleanse effect with beneficial flag 2 removes eligible harmful buffs in the recovered handler. That does not prove every control state in every server path is removed. Target selection and eligibility still matter.",
          "Invincibility is not 100% evasion, and neither is a shield. Forced-hit effects may bypass miss rolls; shield expiry is not healing. Attribute reduction, state removal and shield depletion should be logged as separate events."
        ]
      },
      {
        "id": "test",
        "title": "Test a chain, not a visual impression",
        "paragraphs": [
          "For a status synergy, verify application first, then the target class/condition, then the consuming effect. Keep opponent stats and unrelated buffs fixed. Record application, replacement, cleanse and removal times.",
          "The November 2 public-client comparison found no visible general CC fix. That result does not establish private server behavior. Label a result with build and mode rather than declaring every control effect fixed or broken."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Reliable control with a usable follow-up",
        "reason": "Choose a status the build actually applies and a consumer that recognizes its exact class."
      },
      {
        "tier": "A",
        "title": "Match protection to the incoming threat",
        "reason": "Use the relevant resistance, cleanse or survival tool after verifying what it prevents."
      },
      {
        "tier": "B",
        "title": "Layer compatible effects deliberately",
        "reason": "Distinct identities can coexist, but incoming overlay 2 can erase a planned chain."
      },
      {
        "tier": "C",
        "title": "Delay animation-based synergy claims",
        "reason": "Similar visuals and names do not establish shared state or conditional bonus damage."
      }
    ],
    "checklist": [
      "Identify ID, state, group and class.",
      "Read incoming overlay and tier.",
      "Check exact condition class.",
      "Measure application and removal times.",
      "Separate live results from recovered-client observations."
    ],
    "faq": [
      {
        "q": "Does same group always mean no stacking?",
        "a": "No. Overlay 1 only refreshes the same ID. Incoming overlay 2 is the rule that clears the group."
      },
      {
        "q": "Does cleanse remove every negative state?",
        "a": "Not established. The handler filters eligible attached buffs; target rules and other state paths require verification."
      }
    ]
  },
  "drops": {
    "title": "Drops, draws & probability",
    "summary": "Trace every pool layer before calling a weight a chance. Compare guaranteed value separately from conditional rolls and unresolved pity rules.",
    "sections": [
      {
        "id": "path",
        "title": "A reward has a route, not just one number",
        "paragraphs": [
          "First identify the event or purchase, its selected pool, eligible rows, the row-selection rule, output quantity and any nested pool. A fixed item-and-quantity payload describes the award if granted, not the chance that its prerequisite event occurs.",
          "Quantity fields such as min/max do not state probability. A maximum quantity of ten is not evidence of a 10% chance."
        ]
      },
      {
        "id": "weighted",
        "title": "Weights become shares only within one eligible pool",
        "paragraphs": [
          "For one weighted choice, a row’s conditional share is its weight divided by the sum of eligible alternative weights. If another roll chooses that pool, multiply the conditional chances along the route.",
          "Reward group 110101 has listed nested-group weights 3,000, 4,000, 2,000, 800 and 200. Those sum to 10,000 and correspond to 30%, 40%, 20%, 8% and 2% within that listed parent pool. A specific item inside one group needs its own additional calculation."
        ]
      },
      {
        "id": "eligibility",
        "title": "Eligibility changes the denominator",
        "paragraphs": [
          "Server age, event phase, player state and selected category can change which rows are available. A share computed from every listed row is therefore an unfiltered listed-pool share, not automatically the original server’s exact live odds.",
          "ItemReward rate fields remain raw where the roll semantics are unresolved. Do not turn an ambiguous rate into a precise percentage merely because other tables use a 10,000 scale."
        ]
      },
      {
        "id": "draw-costs",
        "title": "Configured pet and mount draw prices",
        "paragraphs": [
          "The captured ordinary draw rows list one daily free draw each. Event draws can use different configurations and eligibility, so verify the current interface before spending."
        ],
        "table": {
          "headers": [
            "Draw",
            "Single currency",
            "Ten currency",
            "Tickets"
          ],
          "rows": [
            [
              "Pet",
              "300 Bound Diamonds",
              "2,700 Bound Diamonds",
              "1 single / 10 for ten"
            ],
            [
              "Mount",
              "200 Bound Diamonds",
              "1,800 Bound Diamonds",
              "1 single / 10 for ten"
            ]
          ]
        }
      },
      {
        "id": "pity",
        "title": "Milestones are not necessarily replacement pity",
        "paragraphs": [
          "RareCountReward lists draw-count milestone rewards; ItemSafetyReward and Lottery-related tables contain other safety or guarantee configuration. These are different mechanisms, not one universal pity counter.",
          "A ten-pull discount does not prove independent draws or a guaranteed rarity. The original server’s counter transitions, reset rules and replacement behavior are not fully recovered. Keep known milestone awards separate from speculative draw value."
        ]
      },
      {
        "id": "crafting",
        "title": "Forging, affixes and compound success differ",
        "paragraphs": [
          "Workshop weighted outcomes, displayed-quality weights, lucky rewards and random-affix pools have different denominators and rules. Do not join their weights into a single odds calculation.",
          "Success-rate fields also vary by system. EquipCompound’s 6,000 can mean 60% on a 10,000 scale; EquipSuitCompound’s baseSuccess 80 uses a different representation. The table family controls the interpretation."
        ]
      },
      {
        "id": "budget",
        "title": "Price the useful result, not the best picture",
        "paragraphs": [
          "A sound comparison estimates expected useful quantity per currency only after resolving pool layers and eligibility. Count unwanted outcomes by their actual recycle value, not their nominal rarity.",
          "When exact odds are unresolved, compare guaranteed and milestone value first, then label the random component conditional. Set a stop budget before rolling; a possible top prize is not an average return."
        ]
      },
      {
        "id": "changes",
        "title": "Current displayed rewards are not proven server payouts",
        "paragraphs": [
          "The November 2 public-resource comparison reduced six bosses’ displayReward rows: Bound Diamonds 650→600, mount tickets 40→35, pet tickets 40→35 and intermediate gem chests 8→7. The bosses are Smoothie, Daifuku, Perospero, Katakuri, Hawkins and Queen.",
          "Those fields are display payloads. They do not by themselves prove the live award changed. Log the actual received items and current mode before treating a display diff as a confirmed payout rule."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Guaranteed useful value",
        "reason": "Prefer known awards or milestones when they advance the current build efficiently."
      },
      {
        "tier": "A",
        "title": "Resolved eligible pools",
        "reason": "Compare conditional expected value only when pool route, units and eligibility are known."
      },
      {
        "tier": "B",
        "title": "Budgeted speculative rolls",
        "reason": "Use a stop limit and keep uncertain pity value separate."
      },
      {
        "tier": "C",
        "title": "Avoid top-prize-only valuation",
        "reason": "A rare possible item and a raw weight do not establish a good purchase."
      }
    ],
    "checklist": [
      "Trace parent and nested pools.",
      "Filter eligibility before choosing a denominator.",
      "Keep quantity and chance separate.",
      "Separate milestone, safety and ordinary draw rules.",
      "Verify actual payouts when only display fields changed."
    ],
    "faq": [
      {
        "q": "Does a weight of 3,000 always mean 30%?",
        "a": "No. It is 30% only when the relevant eligible alternatives in that draw sum to 10,000."
      },
      {
        "q": "Does buying ten guarantee a quality?",
        "a": "The price discount alone proves no guarantee; the actual guarantee rules must be established separately."
      }
    ]
  },
  "characters": {
    "title": "Character development & skill timing",
    "summary": "Build the exact character variant and skill rank. Stars, level, potential, talents and support systems can change different parts of the kit.",
    "sections": [
      {
        "id": "catalog",
        "title": "Character records are variant-specific",
        "paragraphs": [
          "The captured playable catalog contains 71 characters. GeneralRef supplies base identity and combat fields; GeneralLvRef and GeneralStarRef supply progression; GeneralSkillRef supplies actual level/star-linked skills and attributes. Descriptive skill-group text is not the executable effect.",
          "The captured row maxima are not uniform: 46 characters have level rows through 95 and star rows through 21; 25 have level rows through 115 and star rows through 24. These are table endpoints, not proof every account can unlock them immediately."
        ]
      },
      {
        "id": "skills",
        "title": "Use the unlocked skill variant",
        "paragraphs": [
          "A higher skill variant can change targeting, effects, timing and cooldown, not merely the displayed damage. Compare exact skill IDs at the level and star used in the match.",
          "A catalog’s highest row is not automatically active on the character. A tournament fixed at level 90 and 21 stars must use the actual rules for that snapshot rather than importing maximum-rank behavior."
        ]
      },
      {
        "id": "timing",
        "title": "First hit is an event sequence",
        "paragraphs": [
          "Movement speed, attack interval, range, keep distance, pursue behavior, cast time, effect timing and cooldown are distinct fields. The first landed hit also depends on starting geometry, chosen action, target validity and projectile travel.",
          "A short listed cast is not a guarantee of winning every opening. To compare “fastest,” fix starting positions, action eligibility and loadout, then measure first application over repeated trials. Do not turn a timing table into a universal attacks-per-minute ranking."
        ]
      },
      {
        "id": "potential",
        "title": "Potential is a prerequisite tree",
        "paragraphs": [
          "PotentialRef defines character ownership and node prerequisites. PotentialLvRef supplies level costs, stats and skill entries. Unlocking the route, purchasing the node and applying its effect are separate questions.",
          "Some nodes replace a buff or extend duration. Follow the active entry and account for the recovered-client duration-extension caveat rather than assuming the description’s nominal seconds are measured live behavior."
        ]
      },
      {
        "id": "other-tracks",
        "title": "Talents, echo and Devil Fruits are distinct",
        "paragraphs": [
          "TalentRef and TalentAdvanceRef hold talent progression. GeneralEchoRef holds quality/count/level-related bonuses. GeneralDevilFruitRef defines activation cost, attributes and linked skills. An auxiliary power field is not automatically Attack.",
          "For every track, read the real linked effect and current restriction. There is no sourced universal allocation route for all accounts. Compare a reachable breakpoint against the next best use of that specific currency."
        ]
      },
      {
        "id": "support",
        "title": "Aura, footprints, fleet and team tracks matter",
        "paragraphs": [
          "The character aura/suit track uses SuitTypeRef, SuitStageRef and SuitNumRef and is separate from gear sets. Footprints have their own items, stages and possible expiry behavior. Fleet skills and team-level bonuses are separate again.",
          "Normalize these sources in comparisons. A timed food buff, fleet-skill change or expired appearance effect can change a result without any change to the character skill being tested."
        ]
      },
      {
        "id": "custom",
        "title": "Custom 1v1 builds need explicit inheritance rules",
        "paragraphs": [
          "The project’s proposed format gives equal base stats, level 90 and 21 stars, any two selected S1/S2 skills, a chosen normal sequence, five pet skills and a budgeted loadout. Those are tournament rules, not proof that the original game automatically supports every cross-character interaction.",
          "A passive attached to a selected skill should be traced with that skill; unrelated native passives should not be silently inherited. Fix skill variants, timing, costs, targeting and allowed support effects before comparing builds. The strongest pair depends on whether both selected skills actually function in the custom engine."
        ]
      },
      {
        "id": "audit",
        "title": "Separate missing data from unreleased artwork",
        "paragraphs": [
          "Public build 34521 still has no playable GeneralRef or GeneralSkillRef rows for staged Bullet, Zephyr/Z or Tesoro artwork. A portrait does not establish a kit, rarity or release date.",
          "Earlier recovered-client bug reproductions are bounded by their paths. Poor old character rankings do not diagnose bugs; static coverage is not a live test of every skin, relic, potential and mode."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Make the chosen kit function",
        "reason": "Confirm exact skill variant, targeting, trigger and supported inheritance before optimizing stats."
      },
      {
        "tier": "A",
        "title": "Reach useful skill and potential breakpoints",
        "reason": "Invest where the actual active kit changes meaningfully."
      },
      {
        "tier": "B",
        "title": "Develop support tracks for a defined role",
        "reason": "Compare talents, echo and other tracks by reachable effect and currency cost."
      },
      {
        "tier": "C",
        "title": "Delay unsupported maximum-build assumptions",
        "reason": "Do not rank from staged art, unavailable rows or passives the custom rules do not inherit."
      }
    ],
    "checklist": [
      "Fix exact character and skill IDs.",
      "Check actual unlocks rather than catalog maxima.",
      "Normalize food, fleet, support and temporary effects.",
      "Trace selected-skill passives separately from native passives.",
      "Measure timing under fixed starting geometry."
    ],
    "faq": [
      {
        "q": "Are all characters capped at 21 stars?",
        "a": "No. The capture has two row-endpoint groups: 46 at 21 stars/95 levels and 25 at 24 stars/115 levels. Account eligibility remains separate."
      },
      {
        "q": "Does the shortest cooldown always hit first?",
        "a": "No. Cooldown, action selection, movement, cast/effect time and travel determine different parts of the sequence."
      }
    ]
  },
  "new-player": {
    "title": "New-player planning",
    "summary": "Use a conservative, mechanics-based route while account-specific unlocks and the final starter roster are verified. Avoid spending from an invented universal day-one script.",
    "sections": [
      {
        "id": "scope",
        "title": "What this route can establish",
        "paragraphs": [
          "The recovered source pack deliberately leaves the detailed new-player investment route unfinished. It does not verify a universal starter character, day-one reward schedule, spending assumption or current server event route.",
          "This guide therefore supplies a usable decision workflow grounded in the documented systems. Exact account-stage unlocks and event-specific rewards must be read in the current interface before they become a recommended route."
        ]
      },
      {
        "id": "baseline",
        "title": "Record your account before choosing upgrades",
        "paragraphs": [
          "Write down server age, available modes, roster, character variants, current level/stars, unlocked pet slots, gear sockets and unspent currencies. Include timed buffs and active events.",
          "This baseline prevents an old guide’s expired reward or another account’s unlocked system from becoming a false prerequisite. Do not spend a rare currency merely because a screenshot shows someone else’s stronger account."
        ]
      },
      {
        "id": "core",
        "title": "Choose a small active core by mode",
        "paragraphs": [
          "Pick the characters actually needed for the next accessible content. Check their current skill variants and whether they can reach and hit the enemies. Keep some resources for correcting a bad matchup instead of spreading every currency evenly.",
          "This is an upgrade-priority rule, not a sourced character tier ranking. The correct core depends on available units, restrictions, resources and the account’s immediate objective."
        ]
      },
      {
        "id": "diagnose",
        "title": "Fix the earliest failure in the fight",
        "paragraphs": [
          "If the team dies before using skills, test survival. If attacks miss, test Hit or a compatible direct-hit effect. If the team survives but cannot finish, compare damage factors and useful skill uptime.",
          "Change one category at a time and repeat the same content. A score increase without a changed failure point may not move progression. Read the damage guide before treating similarly named stats as substitutes."
        ]
      },
      {
        "id": "guaranteed",
        "title": "Take reachable guaranteed breakpoints first",
        "paragraphs": [
          "Check affordable gear-set thresholds, legal socket upgrades, useful pet-slot unlocks and collection completions. Use exact current-to-target costs; do not count a future bonus until its requirement is met.",
          "Pet book stages 1, 50, 100, 150 and 200 unlock the five skill slots in the captured configuration. Individual pet skill rank follows a different stage track. This distinction can prevent spending on the wrong bottleneck."
        ]
      },
      {
        "id": "resources",
        "title": "Separate permanent, timed and chance value",
        "paragraphs": [
          "Permanent stats, timed food, random draws and milestone rewards should have separate lines in the plan. A temporary clear can be worthwhile, but it is not permanent account growth.",
          "For draws, use current prices and known milestones; keep unknown server pity behavior out of guaranteed returns. Save resources when the next relevant unlock or event terms are not established instead of inventing an efficiency claim."
        ]
      },
      {
        "id": "routine",
        "title": "Build a routine from verified current resets",
        "paragraphs": [
          "Use the live mode list to record daily and weekly reset times, entry limits, guaranteed rewards and restrictions. The captured standard pet/mount rows list a daily free draw each, but event schedules and account eligibility need current verification.",
          "A complete routine must be tailored to the account and server. Do not publish guessed reset times or expired event actions as mandatory chores. Revisit the plan when a new mode or skill breakpoint changes the bottleneck."
        ]
      },
      {
        "id": "safe-spend",
        "title": "Before an irreversible purchase",
        "paragraphs": [
          "Confirm the exact character variant, recipient group, current-row upgrade cost, actual output and any random or time-limited condition. Read dismantle and combine recipes before consuming gear or gems.",
          "Keep a short before/after note for major changes. That record makes the next decision evidence-based and gives collaborators a reproducible report if a rule or tooltip appears wrong."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Remove the current progression blocker",
        "reason": "Spend on the earliest demonstrated failure using reachable legal upgrades."
      },
      {
        "tier": "A",
        "title": "Collect efficient guaranteed thresholds",
        "reason": "Choose actual set, slot or collection rewards available to this account."
      },
      {
        "tier": "B",
        "title": "Prepare a documented next unlock",
        "reason": "Save with a concrete objective and current requirements."
      },
      {
        "tier": "C",
        "title": "Delay unverified starter and event scripts",
        "reason": "Do not pay based on expired rewards, guessed resets or a universal roster claim."
      }
    ],
    "checklist": [
      "Record account stage and current legal systems.",
      "Choose the immediate mode and its blocker.",
      "Separate permanent gains from timed and random value.",
      "Verify costs and recipes before consuming.",
      "Update the plan after a meaningful unlock."
    ],
    "faq": [
      {
        "q": "Which starter should every player max first?",
        "a": "The recovered evidence does not establish a universal answer. Account roster, mode restrictions and current skill access must determine that route."
      },
      {
        "q": "Is this a verified day-by-day launch plan?",
        "a": "No. It is a practical mechanics-based planning route; account-stage unlocks, resets and starter investments still require current verification."
      }
    ]
  },
  "halloween": {
    "title": "Halloween pets & seasonal choices",
    "summary": "Ghost, Chopper and Karoo solve different problems. Their skills and corrected collection group are documented; current event prices and availability require the active event rules.",
    "sections": [
      {
        "id": "scope",
        "title": "Separate seasonal availability from permanent mechanics",
        "paragraphs": [
          "The captured pet rows document Halloween Ghost, Halloween Chopper and Halloween Karoo. They do not by themselves prove a current shop price, event date, free acquisition route or future rerun.",
          "Compare the skill you need with the actual event’s acquisition cost and stage requirements. Artwork or a seasonal label is not a promise that an item can be obtained now."
        ]
      },
      {
        "id": "ghost",
        "title": "Ghost improves lifesteal amount",
        "paragraphs": [
          "At skill rank 5, Ghost adds 84 percentage points to lifesteal amount for 20 seconds, with a listed 30-second cooldown. It does not add lifesteal proc chance.",
          "A fighter needs a qualifying lifesteal route and enough landed damage to use it. Opposing amount resistance and healing reduction can limit recovery, while early burst can prevent the sustain window from mattering."
        ]
      },
      {
        "id": "chopper",
        "title": "Chopper counters lifesteal amount",
        "paragraphs": [
          "At rank 5, Halloween Chopper adds 84 percentage points of lifesteal amount resistance for 20 seconds on a listed 30-second cooldown. It targets the amount coefficient, not the opponent’s chance to proc lifesteal.",
          "Its value is matchup-specific. It can directly contest Ghost’s amount contribution while active, but it is not a universal anti-healing effect and should not be assumed to suppress every heal or shield."
        ]
      },
      {
        "id": "karoo",
        "title": "Karoo combines harmful-buff removal and healing",
        "paragraphs": [
          "At rank 5, Karoo applies a harmful-buff-removal effect and a heal of 22.5% of source Attack every 500 ms for a 6,100 ms lifetime. The nominal rate is 45% source Attack per second, with a listed 30-second cooldown.",
          "The removal handler selects beneficial flag 2. The tooltip’s broad target wording is not proof of every live recipient or every state being removed. Skill ownership, target construction and server behavior need the actual fight path."
        ]
      },
      {
        "id": "unlocks",
        "title": "Numeric stages beat misleading unlock text",
        "paragraphs": [
          "The captured rank-5 numeric requirement is pet stage 9 for all three pets. Some descriptions mention stage 5; that is a text mismatch, not the numeric unlock rule.",
          "Check the current interface lock before spending. Do not confuse rank 5, individual pet stage 9 and pet book stage 200 for the fifth equipped slot: those are three different milestones."
        ]
      },
      {
        "id": "collection",
        "title": "Group 16 was corrected in build 34521",
        "paragraphs": [
          "The November 2 public-resource comparison changed pet collection group 16 from Inuarashi puppy + Ghost + Chopper to Ghost + Chopper + Karoo. Its reward stayed Crit rating +108 and Anti-Crit rating +108.",
          "The change concerns pet IDs, not staged unreleased characters with similar number endings. Count the collection reward once and verify whether the active client shows the corrected members."
        ]
      },
      {
        "id": "stacking",
        "title": "Apply the same buff rules as every pet",
        "paragraphs": [
          "Ghost’s amount buff, Chopper’s amount resistance and Karoo’s heal are different jobs. Do not infer competition because all three are seasonal. Incoming overlay, ID and group determine replacement and coexistence.",
          "Karoo’s heal has a distinct overlay-1 ID in group 48, allowing coexistence with other distinct overlay-1 healing IDs. Reapplying its own ID refreshes it rather than creating a second independent copy."
        ]
      },
      {
        "id": "choice",
        "title": "Choose from the fight, then price the event",
        "paragraphs": [
          "For a build with real lifesteal procs and damage uptime, test Ghost. Against an opponent relying on lifesteal amount, test Chopper. For eligible harmful buffs and a surviving heal window, test Karoo.",
          "These are use-case priorities, not a universal seasonal ranking. Include stage-up cost, slot availability, collection completion and the event’s confirmed currency rules before deciding which purchase is most efficient."
        ]
      }
    ],
    "priorities": [
      {
        "tier": "S",
        "title": "Karoo when cleanse and recovery decide the fight",
        "reason": "Useful when eligible harmful buffs matter and the fighter survives to receive healing; confirm target behavior."
      },
      {
        "tier": "A",
        "title": "Ghost on a functioning lifesteal build",
        "reason": "Strong amount contribution requires actual proc chance and landed damage."
      },
      {
        "tier": "B",
        "title": "Chopper into lifesteal-dependent opponents",
        "reason": "A specialized counter to amount, not a universal block on every healing source."
      },
      {
        "tier": "C",
        "title": "Delay unpriced seasonal completion",
        "reason": "Do not infer event costs or availability from permanent pet data; price the corrected collection separately."
      }
    ],
    "checklist": [
      "Use numeric rank-5 requirement: pet stage 9.",
      "Do not confuse amount with proc chance.",
      "Verify Karoo’s eligible removal and recipients.",
      "Use corrected Ghost/Chopper/Karoo collection membership.",
      "Check the active event’s real costs and availability."
    ],
    "faq": [
      {
        "q": "Does Ghost grant 84% lifesteal chance?",
        "a": "No. It adds 84 percentage points to lifesteal amount; chance is a separate attribute."
      },
      {
        "q": "Does Chopper stop all healing?",
        "a": "No. Its documented bonus is lifesteal amount resistance, not universal healing reduction."
      },
      {
        "q": "Is rank 5 unlocked at stage 5?",
        "a": "The captured numeric requirement is stage 9. Some tooltip text conflicts; verify the interface before purchase."
      }
    ]
  }
};
