window.HELP_IMPROVE_VIDEOJS = false;


$(document).ready(function() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    function loadCharacterSheet() {
        fetch('http://127.0.0.1:5000/character')
            .then(response => response.json())
            .then(data => {
                // Header
                document.getElementById('char-name').textContent = data.name;
                document.getElementById('char-race').textContent = data.race;
                document.getElementById('char-class-level').textContent = `${data.class} ${data.level}`;
                document.getElementById('char-alignment').textContent = data.alignment;

                // Ability Scores
                for (const [ability, values] of Object.entries(data.ability_scores)) {
                    document.getElementById(`char-${ability.substring(0, 3)}-score`).textContent = values.score;
                    document.getElementById(`char-${ability.substring(0, 3)}-mod`).textContent = `${values.modifier >= 0 ? '+' : ''}${values.modifier}`;
                }

                // Combat Stats
                document.getElementById('char-ac').textContent = data.combat.armor_class;
                document.getElementById('char-initiative').textContent = `+${data.combat.initiative}`;
                document.getElementById('char-speed').textContent = `${data.combat.speed}ft`;

                // HP
                document.getElementById('char-hp-current').textContent = data.combat.hit_points.current;
                document.getElementById('char-hp-max').textContent = data.combat.hit_points.max;
                
                // Skills
                const skillsContainer = document.getElementById('char-skills');
                skillsContainer.innerHTML = '';
                for (const [skill, values] of Object.entries(data.skills)) {
                    const skillElement = document.createElement('p');
                    const prof_icon = values.proficient ? '●' : '○';
                    skillElement.textContent = `${prof_icon} ${skill.charAt(0).toUpperCase() + skill.slice(1)}: ${values.modifier >= 0 ? '+' : ''}${values.modifier}`;
                    skillsContainer.appendChild(skillElement);
                }
                
                // Proficiencies, Languages, Features
                const profsLangsContainer = document.getElementById('char-proficiencies-languages');
                profsLangsContainer.innerHTML = `<p><strong>Armor:</strong> ${data.proficiencies_and_languages.armor.join(', ') || 'None'}</p>
                                                 <p><strong>Weapons:</strong> ${data.proficiencies_and_languages.weapons.join(', ')}</p>
                                                 <p><strong>Languages:</strong> ${data.proficiencies_and_languages.languages.join(', ')}</p>`;
                
                const featuresContainer = document.getElementById('char-features');
                featuresContainer.innerHTML = data.features_and_traits.join(', ');

                // Equipment
                const equipmentContainer = document.getElementById('char-equipment');
                equipmentContainer.innerHTML = `<p><strong>Money:</strong> ${data.equipment.money.gp} gp</p>
                                                <p><strong>Items:</strong> ${data.equipment.items.join(', ')}</p>`;

                // Spellcasting
                const spellcastingContainer = document.getElementById('char-spellcasting');
                spellcastingContainer.innerHTML = `<p><strong>Ability:</strong> ${data.spellcasting.spellcasting_ability}</p>
                                                   <p><strong>Save DC:</strong> ${data.spellcasting.spell_save_dc}</p>
                                                   <p><strong>Attack Bonus:</strong> +${data.spellcasting.spell_attack_bonus}</p>
                                                   <p><strong>Cantrips:</strong> ${data.spellcasting.spells_known.cantrips.join(', ')}</p>
                                                   <p><strong>Lvl 1 Spells:</strong> ${data.spellcasting.spells_known.level_1.join(', ')}</p>
                                                   <p><strong>Lvl 1 Slots:</strong> ${data.spellcasting.spell_slots.level_1.used} / ${data.spellcasting.spell_slots.level_1.total}</p>`;
            })
            .catch(error => console.error('Error loading character sheet:', error));
    }

    function addActionSummary(actionSummary) {
        const actionLog = document.getElementById('action-log');
        
        // Remove placeholder text if present
        if (actionLog.querySelector('.has-text-grey-light')) {
            actionLog.innerHTML = '';
        }
        
        // Add each mechanic as a separate line
        if (actionSummary.mechanics && actionSummary.mechanics.length > 0) {
            actionSummary.mechanics.forEach(mechanic => {
                const mechanicElement = document.createElement('p');
                
                // Add appropriate class based on the mechanic text
                if (mechanic.includes('✓') || mechanic.includes('Successfully')) {
                    mechanicElement.classList.add('action-success');
                } else if (mechanic.includes('❌') || mechanic.includes('not') || mechanic.includes('Cannot')) {
                    mechanicElement.classList.add('action-failure');
                } else {
                    mechanicElement.classList.add('action-info');
                }
                
                mechanicElement.textContent = mechanic;
                actionLog.appendChild(mechanicElement);
            });
        }
        
        // Keep only last 20 mechanics (about 2-3 actions)
        while (actionLog.children.length > 20) {
            actionLog.removeChild(actionLog.firstChild);
        }
        
        // Scroll to bottom
        actionLog.scrollTop = actionLog.scrollHeight;
    }
    
    function updateNPCHealthBars(npcs) {
        const healthBarsContainer = document.getElementById('npc-health-bars');
        
        if (!npcs || Object.keys(npcs).length === 0) {
            healthBarsContainer.innerHTML = '<p class="has-text-grey-light">No active encounters</p>';
            return;
        }
        
        healthBarsContainer.innerHTML = '';
        
        for (const [name, data] of Object.entries(npcs)) {
            const npcItem = document.createElement('div');
            npcItem.classList.add('npc-health-item');
            
            const npcName = document.createElement('div');
            npcName.classList.add('npc-name');
            
            const healthPercent = Math.round((data.hp / data.max_hp) * 100);
            
            npcName.innerHTML = `<span>${name}</span><span>${data.hp}/${data.max_hp} HP</span>`;
            
            const healthBarContainer = document.createElement('div');
            healthBarContainer.classList.add('health-bar-container');
            
            const healthBar = document.createElement('div');
            healthBar.classList.add('health-bar');
            healthBar.style.width = `${healthPercent}%`;
            healthBar.textContent = `${healthPercent}%`;
            
            // Color based on health percentage
            if (healthPercent > 60) {
                healthBar.classList.add('healthy');
            } else if (healthPercent > 30) {
                healthBar.classList.add('injured');
            } else {
                healthBar.classList.add('critical');
            }
            
            healthBarContainer.appendChild(healthBar);
            npcItem.appendChild(npcName);
            npcItem.appendChild(healthBarContainer);
            healthBarsContainer.appendChild(npcItem);
        }
    }

    function addMessage(message, isUser, characterName, characterPortrait) {
        const messageWrapper = document.createElement('div');
        messageWrapper.classList.add('message');
        messageWrapper.classList.add(isUser ? 'is-user' : 'is-primary');

        const messageBody = document.createElement('div');
        messageBody.classList.add('message-body');

        if (!isUser) {
            const characterInfo = document.createElement('div');
            characterInfo.classList.add('character-info');

            if (characterPortrait) {
                const portrait = document.createElement('img');
                portrait.src = characterPortrait;
                portrait.classList.add('character-portrait');
                characterInfo.appendChild(portrait);
            }

            if (characterName) {
                const name = document.createElement('div');
                name.classList.add('character-name');
                name.textContent = characterName;
                characterInfo.appendChild(name);
            }
            messageWrapper.appendChild(characterInfo);
        }

        const messageText = document.createElement('div');
        messageText.textContent = message;
        messageBody.appendChild(messageText);

        messageWrapper.appendChild(messageBody);
        chatMessages.appendChild(messageWrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function sendMessage() {
        const message = userInput.value.trim();
        if (message) {
            addMessage(message, true);
            userInput.value = '';
            
            // Send message to the backend and get the response
            fetch('http://127.0.0.1:5000/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message }),
            })
            .then(response => {
                if (!response.ok) {
                    // Log the full text of the response if it's not a success
                    return response.text().then(text => {
                        throw new Error(`Server responded with ${response.status}: ${text}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                // NEW: Check for clarification question first
                if (data.clarification_question) {
                    addMessage(data.clarification_question, false, data.character_name, data.character_portrait);
                } else {
                    // Normal narrative response
                    addMessage(data.response, false, data.character_name, data.character_portrait);
                
                    // Update action summary
                    if (data.action_summary) {
                        addActionSummary(data.action_summary);
                    }
                    
                    // Update NPC health bars
                    if (data.npcs) {
                        updateNPCHealthBars(data.npcs);
                    }
                }
            })
            .catch((error) => {
                console.error('Error sending message:', error);
                let errorMessage = "Sorry, I'm having trouble connecting to my brain...";
                if (error && error.message) {
                    errorMessage = `Error: ${error.message}`;
                }
                addMessage(errorMessage, false);
            });
        }
    }

    sendButton.addEventListener('click', sendMessage);

    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Load the character sheet when the page loads
    loadCharacterSheet();
})
