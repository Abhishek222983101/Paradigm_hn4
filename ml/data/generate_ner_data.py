"""
NER Training Data Generator for TraceFlow AI
Generates 500+ training samples for entity extraction from natural language inputs
about recycled material traceability operations.

Entities to extract:
- MATERIAL: Type of material (PET flakes, HDPE pellets, Mixed plastic bales, etc.)
- QUANTITY: Numeric quantity (500, 1000, 25.5, etc.)
- UNIT: Unit of measurement (kg, tonnes, MT, pieces, bales, etc.)
- VENDOR: Supplier or customer name
- DATE: Date references (today, yesterday, March 15, 2024-03-15, etc.)
- LOCATION: Warehouse or facility name
- PROCESS: Process type (purchase, wash, segregate, dispatch, QC, etc.)
- BATCH_ID: Batch or lot identifiers
- QUALITY_GRADE: Grade levels (A, B, C, Premium, Rejected, etc.)
- PRICE: Price values with currency
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# Domain-specific vocabularies
MATERIALS = [
    "PET flakes",
    "HDPE pellets",
    "PP granules",
    "LDPE film",
    "mixed plastic bales",
    "recycled PET",
    "rPET chips",
    "HDPE regrind",
    "PP regrind",
    "plastic scrap",
    "post-consumer PET",
    "post-industrial HDPE",
    "colored PET",
    "clear PET",
    "natural HDPE",
    "black HDPE",
    "food-grade PET",
    "bottle-grade PET",
    "mixed rigid plastics",
    "flexible film waste",
    "PET preforms",
    "HDPE bottles",
    "stretch film",
    "shrink wrap",
    "agricultural film",
    "PVC scrap",
]

VENDORS = [
    "GreenCycle Industries",
    "EcoPlast Solutions",
    "RecycleMax Corp",
    "PureStream Materials",
    "CircularPoly Ltd",
    "ReNew Plastics",
    "EnviroCollect Inc",
    "CleanChain Supply",
    "SustainaPack",
    "EcoMat Trading",
    "PlastiCycle Co",
    "GreenLoop Suppliers",
    "RecoverTech Materials",
    "ClearStream Plastics",
    "NatureCycle",
    "EarthFirst Materials",
]

LOCATIONS = [
    "Main Warehouse",
    "Processing Facility A",
    "Storage Unit B",
    "Distribution Center",
    "Sorting Station 1",
    "Washing Plant",
    "Pelletizing Unit",
    "QC Lab",
    "Dispatch Bay",
    "Receiving Dock",
    "Holding Area",
    "Finished Goods Store",
    "Raw Material Store",
    "Reject Storage",
    "Quarantine Zone",
]

UNITS = [
    "kg",
    "tonnes",
    "MT",
    "pieces",
    "bales",
    "bags",
    "containers",
    "pallets",
    "tons",
]

QUALITY_GRADES = [
    "Grade A",
    "Grade B",
    "Grade C",
    "Premium",
    "Standard",
    "Rejected",
    "A+",
    "B-",
    "Food Grade",
    "Technical Grade",
]

PROCESSES = {
    "PR": ["purchased", "procured", "received", "bought", "acquired"],
    "SEG": ["segregated", "sorted", "separated", "classified"],
    "MB": ["made batch", "created batch", "batched", "combined into batch"],
    "WT": ["washed", "cleaned", "processed through wash", "treated"],
    "WTR": ["rewashed", "re-cleaned", "washed again", "retreated"],
    "QC": [
        "quality checked",
        "inspected",
        "tested",
        "QC passed",
        "QC failed",
        "graded",
    ],
    "SD": ["dispatched", "shipped", "sent", "delivered", "sold"],
}

# Templates for different intents
TEMPLATES = {
    "data_entry": {
        "purchase": [
            "We {process} {quantity} {unit} of {material} from {vendor}",
            "{quantity} {unit} {material} received from {vendor} {date}",
            "Got {quantity} {unit} of {material} from {vendor} at {location}",
            "Incoming shipment: {quantity} {unit} {material} from {vendor}",
            "{vendor} delivered {quantity} {unit} of {material} {date}",
            "Log purchase of {quantity} {unit} {material} from {vendor}",
            "Record {quantity} {unit} {material} bought from {vendor} for {price}",
            "Add entry for {quantity} {unit} of {material} received at {location}",
            "New stock: {quantity} {unit} {material} from {vendor}",
            "Register incoming {material} - {quantity} {unit} from {vendor}",
        ],
        "segregation": [
            "Segregated {quantity} {unit} of {material} into {quality_grade}",
            "Sorted {material} batch - {quantity} {unit} as {quality_grade}",
            "Split {material} into {quality_grade} category - {quantity} {unit}",
            "Classified {quantity} {unit} {material} as {quality_grade}",
            "Separated out {quantity} {unit} of {quality_grade} {material}",
            "{quantity} {unit} {material} sorted at {location}",
            "Completed segregation of {material} batch at {location}",
        ],
        "washing": [
            "Washed {quantity} {unit} of {material}",
            "Processed {quantity} {unit} {material} through wash line",
            "Cleaning completed for {quantity} {unit} {material}",
            "{material} wash done - {quantity} {unit} output",
            "Washing treatment finished for batch of {material}",
            "Ran {quantity} {unit} {material} through washing at {location}",
        ],
        "quality_check": [
            "QC result for {material}: {quality_grade}",
            "{quantity} {unit} {material} passed QC as {quality_grade}",
            "Quality inspection: {material} graded as {quality_grade}",
            "Tested {quantity} {unit} {material} - result: {quality_grade}",
            "QC failed for {quantity} {unit} of {material}",
            "Inspection complete - {material} is {quality_grade}",
            "Batch of {material} tested and approved as {quality_grade}",
        ],
        "dispatch": [
            "Dispatched {quantity} {unit} of {material} to {vendor}",
            "Shipped {quantity} {unit} {material} to {vendor} {date}",
            "Sent out {quantity} {unit} {material} from {location}",
            "Delivery to {vendor}: {quantity} {unit} {material}",
            "Outgoing shipment - {quantity} {unit} {material} to {vendor}",
            "Sold {quantity} {unit} {material} to {vendor} for {price}",
            "{vendor} picked up {quantity} {unit} of {material}",
        ],
        "batch_creation": [
            "Created batch from {quantity} {unit} of {material}",
            "Combined materials into batch - {quantity} {unit} total",
            "New batch: {quantity} {unit} {material} at {location}",
            "Made batch {batch_id} from {material}",
            "Merged {material} inputs - batch {batch_id}",
        ],
        "inventory_update": [
            "Current stock of {material}: {quantity} {unit}",
            "Update inventory: {material} is now {quantity} {unit}",
            "Stock adjustment for {material} at {location}",
            "Inventory count: {quantity} {unit} of {material}",
            "{material} stock at {location} is {quantity} {unit}",
        ],
    },
    "query": {
        "quantity": [
            "How much {material} do we have?",
            "What's the current stock of {material}?",
            "Check inventory for {material}",
            "How many {unit} of {material} in {location}?",
            "Total {material} available?",
            "What's our {material} inventory?",
            "Show me {material} stock levels",
        ],
        "history": [
            "Show transactions for {material}",
            "What did we purchase {date}?",
            "List all purchases from {vendor}",
            "History of {material} at {location}",
            "What happened to batch {batch_id}?",
            "Show me all {material} movements",
            "Transaction history for {date}",
        ],
        "traceability": [
            "Trace the journey of {batch_id}",
            "Where did this {material} come from?",
            "Show lineage for {material} batch",
            "What's the source of {material} at {location}?",
            "Track {material} from {vendor}",
            "Trace back {material} to origin",
            "Show material flow for {batch_id}",
        ],
        "analytics": [
            "What's the yield for {material}?",
            "Show loss percentage for {process}",
            "How much did we dispatch {date}?",
            "Total purchases from {vendor}?",
            "Average quality grade for {material}?",
            "What's our throughput for {date}?",
            "Compare yields across materials",
        ],
        "vendor": [
            "How much have we bought from {vendor}?",
            "List all transactions with {vendor}",
            "What materials from {vendor}?",
            "Pending orders from {vendor}?",
            "{vendor} delivery history",
        ],
    },
}


# Date generators
def generate_date():
    options = [
        "today",
        "yesterday",
        "last week",
        "last month",
        "this morning",
        "on Monday",
        "on Friday",
        "last Tuesday",
        "this week",
    ]
    if random.random() > 0.5:
        days_ago = random.randint(0, 90)
        date = datetime.now() - timedelta(days=days_ago)
        formats = [
            date.strftime("%Y-%m-%d"),
            date.strftime("%B %d"),
            date.strftime("%d/%m/%Y"),
            date.strftime("%d %b %Y"),
        ]
        return random.choice(formats)
    return random.choice(options)


def generate_quantity():
    if random.random() > 0.7:
        return str(round(random.uniform(0.5, 100), 1))
    return str(random.randint(10, 10000))


def generate_price():
    amount = random.randint(100, 50000)
    currencies = ["$", "Rs.", "EUR ", "INR "]
    return f"{random.choice(currencies)}{amount}"


def generate_batch_id():
    prefixes = ["B", "BATCH", "LOT", "BT"]
    return f"{random.choice(prefixes)}-{random.randint(1000, 9999)}"


def extract_entities_from_filled_template(template, values):
    """Extract entity spans from a filled template."""
    entities = []
    text = template

    for key, value in values.items():
        if f"{{{key}}}" in template:
            # Find position of placeholder
            placeholder = f"{{{key}}}"
            pos = text.find(value)
            if pos != -1:
                entity_type = key.upper()
                # Map template keys to entity types
                type_mapping = {
                    "MATERIAL": "MATERIAL",
                    "QUANTITY": "QUANTITY",
                    "UNIT": "UNIT",
                    "VENDOR": "VENDOR",
                    "DATE": "DATE",
                    "LOCATION": "LOCATION",
                    "PROCESS": "PROCESS",
                    "BATCH_ID": "BATCH_ID",
                    "QUALITY_GRADE": "QUALITY_GRADE",
                    "PRICE": "PRICE",
                }
                if entity_type in type_mapping:
                    entities.append(
                        {
                            "start": pos,
                            "end": pos + len(value),
                            "label": type_mapping[entity_type],
                            "text": value,
                        }
                    )

    return entities


def generate_sample(intent_category, intent_type, template):
    """Generate a single training sample."""
    values = {
        "material": random.choice(MATERIALS),
        "quantity": generate_quantity(),
        "unit": random.choice(UNITS),
        "vendor": random.choice(VENDORS),
        "date": generate_date(),
        "location": random.choice(LOCATIONS),
        "quality_grade": random.choice(QUALITY_GRADES),
        "batch_id": generate_batch_id(),
        "price": generate_price(),
    }

    # Add process verb
    process_types = list(PROCESSES.keys())
    if "purchase" in intent_type or "procured" in template.lower():
        values["process"] = random.choice(PROCESSES["PR"])
    elif "segregat" in intent_type or "sort" in template.lower():
        values["process"] = random.choice(PROCESSES["SEG"])
    elif "wash" in intent_type or "clean" in template.lower():
        values["process"] = random.choice(PROCESSES["WT"])
    elif "dispatch" in intent_type or "ship" in template.lower():
        values["process"] = random.choice(PROCESSES["SD"])
    elif "qc" in intent_type.lower() or "quality" in template.lower():
        values["process"] = random.choice(PROCESSES["QC"])
    else:
        values["process"] = random.choice(PROCESSES[random.choice(process_types)])

    # Fill template
    text = template
    for key, value in values.items():
        text = text.replace(f"{{{key}}}", value)

    # Extract entities
    entities = []
    for key, value in values.items():
        pos = text.find(value)
        if pos != -1 and f"{{{key}}}" in template:
            entity_type = key.upper()
            entities.append(
                {
                    "start": pos,
                    "end": pos + len(value),
                    "label": entity_type,
                    "text": value,
                }
            )

    # Sort entities by start position
    entities = sorted(entities, key=lambda x: x["start"])

    return {
        "text": text,
        "intent": f"{intent_category}.{intent_type}",
        "entities": entities,
    }


def generate_dataset(num_samples=600):
    """Generate the complete training dataset."""
    samples = []

    # Calculate samples per template
    all_templates = []
    for intent_category, intents in TEMPLATES.items():
        for intent_type, templates in intents.items():
            for template in templates:
                all_templates.append((intent_category, intent_type, template))

    samples_per_template = num_samples // len(all_templates) + 1

    for intent_category, intent_type, template in all_templates:
        for _ in range(samples_per_template):
            sample = generate_sample(intent_category, intent_type, template)
            samples.append(sample)

    # Shuffle and trim to exact count
    random.shuffle(samples)
    samples = samples[:num_samples]

    return samples


def generate_intent_classification_data(samples):
    """Generate intent classification training data from NER samples."""
    intent_data = []
    for sample in samples:
        intent_data.append({"text": sample["text"], "intent": sample["intent"]})
    return intent_data


def convert_to_bio_format(samples):
    """Convert samples to BIO tagging format for sequence labeling."""
    bio_samples = []

    for sample in samples:
        text = sample["text"]
        entities = sample["entities"]

        # Simple word-level tokenization
        words = text.split()
        labels = ["O"] * len(words)

        # Map character positions to word indices
        char_to_word = {}
        current_pos = 0
        for i, word in enumerate(words):
            for j in range(len(word)):
                char_to_word[current_pos + j] = i
            current_pos += len(word) + 1  # +1 for space

        # Assign BIO labels
        for entity in entities:
            start, end = entity["start"], entity["end"]
            label = entity["label"]

            # Find words that overlap with this entity
            entity_word_indices = set()
            for char_pos in range(start, end):
                if char_pos in char_to_word:
                    entity_word_indices.add(char_to_word[char_pos])

            entity_word_indices = sorted(entity_word_indices)

            for i, word_idx in enumerate(entity_word_indices):
                if i == 0:
                    labels[word_idx] = f"B-{label}"
                else:
                    labels[word_idx] = f"I-{label}"

        bio_samples.append(
            {"tokens": words, "labels": labels, "intent": sample["intent"]}
        )

    return bio_samples


def main():
    print("Generating NER training data for TraceFlow AI...")

    # Set seed for reproducibility
    random.seed(42)

    # Generate samples
    samples = generate_dataset(num_samples=600)

    print(f"Generated {len(samples)} samples")

    # Calculate intent distribution
    intent_counts = {}
    for sample in samples:
        intent = sample["intent"]
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

    print("\nIntent distribution:")
    for intent, count in sorted(intent_counts.items()):
        print(f"  {intent}: {count}")

    # Save raw samples
    output_dir = Path(__file__).parent

    with open(output_dir / "ner_training_data.json", "w") as f:
        json.dump(samples, f, indent=2)
    print(f"\nSaved NER data to {output_dir / 'ner_training_data.json'}")

    # Generate intent classification data
    intent_data = generate_intent_classification_data(samples)
    with open(output_dir / "intent_training_data.json", "w") as f:
        json.dump(intent_data, f, indent=2)
    print(f"Saved intent data to {output_dir / 'intent_training_data.json'}")

    # Generate BIO format for sequence labeling
    bio_samples = convert_to_bio_format(samples)
    with open(output_dir / "ner_bio_format.json", "w") as f:
        json.dump(bio_samples, f, indent=2)
    print(f"Saved BIO format data to {output_dir / 'ner_bio_format.json'}")

    # Generate train/val/test splits
    random.shuffle(samples)
    train_size = int(0.8 * len(samples))
    val_size = int(0.1 * len(samples))

    train_data = samples[:train_size]
    val_data = samples[train_size : train_size + val_size]
    test_data = samples[train_size + val_size :]

    splits = {"train": train_data, "validation": val_data, "test": test_data}

    with open(output_dir / "ner_splits.json", "w") as f:
        json.dump(splits, f, indent=2)
    print(f"Saved train/val/test splits to {output_dir / 'ner_splits.json'}")
    print(f"  Train: {len(train_data)}, Val: {len(val_data)}, Test: {len(test_data)}")

    # Print some examples
    print("\n" + "=" * 60)
    print("Sample training examples:")
    print("=" * 60)
    for i in range(5):
        sample = samples[i]
        print(f"\nExample {i + 1}:")
        print(f"  Text: {sample['text']}")
        print(f"  Intent: {sample['intent']}")
        print(f"  Entities:")
        for entity in sample["entities"]:
            print(f"    - {entity['label']}: '{entity['text']}'")


if __name__ == "__main__":
    main()
