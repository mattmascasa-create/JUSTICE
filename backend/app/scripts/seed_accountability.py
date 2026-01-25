"""
Seed script for Officer Accountability Database
Creates sample departments, officers, and violations for demo/testing
"""
import asyncio
import random
from datetime import datetime, timezone, timedelta
from app.db.database import db
from app.services.accountability import accountability_service
from app.models.accountability import ViolationType, ViolationSeverity, ViolationOutcome, DisciplinaryAction


# Major US police departments with realistic data
SAMPLE_DEPARTMENTS = [
    {"name": "Los Angeles Police Department", "city": "Los Angeles", "state": "CA", "officers": 9000},
    {"name": "New York Police Department", "city": "New York", "state": "NY", "officers": 36000},
    {"name": "Chicago Police Department", "city": "Chicago", "state": "IL", "officers": 12000},
    {"name": "Houston Police Department", "city": "Houston", "state": "TX", "officers": 5400},
    {"name": "Phoenix Police Department", "city": "Phoenix", "state": "AZ", "officers": 3000},
    {"name": "Philadelphia Police Department", "city": "Philadelphia", "state": "PA", "officers": 6500},
    {"name": "San Antonio Police Department", "city": "San Antonio", "state": "TX", "officers": 2500},
    {"name": "San Diego Police Department", "city": "San Diego", "state": "CA", "officers": 2000},
    {"name": "Dallas Police Department", "city": "Dallas", "state": "TX", "officers": 3500},
    {"name": "Austin Police Department", "city": "Austin", "state": "TX", "officers": 1800},
    {"name": "Miami Police Department", "city": "Miami", "state": "FL", "officers": 1400},
    {"name": "Atlanta Police Department", "city": "Atlanta", "state": "GA", "officers": 2000},
    {"name": "Seattle Police Department", "city": "Seattle", "state": "WA", "officers": 1400},
    {"name": "Denver Police Department", "city": "Denver", "state": "CO", "officers": 1500},
    {"name": "Boston Police Department", "city": "Boston", "state": "MA", "officers": 2100},
    {"name": "Detroit Police Department", "city": "Detroit", "state": "MI", "officers": 2500},
    {"name": "Minneapolis Police Department", "city": "Minneapolis", "state": "MN", "officers": 800},
    {"name": "Las Vegas Metro Police", "city": "Las Vegas", "state": "NV", "officers": 3000},
    {"name": "Portland Police Bureau", "city": "Portland", "state": "OR", "officers": 900},
    {"name": "Baltimore Police Department", "city": "Baltimore", "state": "MD", "officers": 2500},
]

FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David", "Joseph", "Thomas", "Charles", "Christopher",
               "Daniel", "Matthew", "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth",
               "Maria", "Jennifer", "Linda", "Patricia", "Barbara", "Elizabeth", "Susan", "Jessica", "Sarah", "Karen"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
              "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]

RANKS = ["Officer", "Sergeant", "Lieutenant", "Captain", "Detective"]

UNITS = ["Patrol", "Traffic", "Narcotics", "Homicide", "Gang Unit", "K-9", "SWAT", "Community Relations"]

VIOLATION_TYPES = list(ViolationType)
SEVERITIES = list(ViolationSeverity)
OUTCOMES = [ViolationOutcome.SUSTAINED, ViolationOutcome.NOT_SUSTAINED, ViolationOutcome.PENDING, ViolationOutcome.EXONERATED]
ACTIONS = [DisciplinaryAction.NONE, DisciplinaryAction.VERBAL_WARNING, DisciplinaryAction.WRITTEN_WARNING, 
           DisciplinaryAction.SUSPENSION, DisciplinaryAction.TERMINATION]


async def seed_departments():
    """Create sample departments"""
    print("Seeding departments...")
    
    for dept_data in SAMPLE_DEPARTMENTS:
        # Check if exists
        existing = await db.accountability_departments.find_one({"name": dept_data["name"]})
        if existing:
            print(f"  Department {dept_data['name']} already exists")
            continue
        
        from app.models.accountability import DepartmentCreate
        data = DepartmentCreate(
            name=dept_data["name"],
            city=dept_data["city"],
            state=dept_data["state"],
            jurisdiction_type="municipal",
            total_officers=dept_data["officers"]
        )
        
        result = await accountability_service.create_department(data, "system_seed")
        if result.get("success"):
            print(f"  Created: {dept_data['name']}")
        else:
            print(f"  Failed: {dept_data['name']} - {result.get('error')}")
    
    print(f"Departments seeded: {await db.accountability_departments.count_documents({})}")


async def seed_officers():
    """Create sample officers with some having violations"""
    print("\nSeeding officers...")
    
    departments = await db.accountability_departments.find({}, {"_id": 0}).to_list(100)
    
    for dept in departments:
        # Create 5-15 officers per department for demo
        num_officers = random.randint(5, 15)
        
        for i in range(num_officers):
            badge_num = f"{random.randint(1000, 9999)}"
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            
            # Check if badge already exists
            existing = await db.officers.find_one({
                "badge_number": badge_num,
                "department_id": dept["department_id"]
            })
            if existing:
                continue
            
            from app.models.accountability import OfficerCreate
            data = OfficerCreate(
                badge_number=badge_num,
                department_id=dept["department_id"],
                first_name=first,
                last_name=last,
                rank=random.choice(RANKS),
                unit=random.choice(UNITS),
                hire_date=(datetime.now() - timedelta(days=random.randint(365, 7300))).strftime("%Y-%m-%d")
            )
            
            await accountability_service.create_officer(data, "system_seed")
    
    print(f"Officers seeded: {await db.officers.count_documents({})}")


async def seed_violations():
    """Create sample violations for some officers"""
    print("\nSeeding violations...")
    
    officers = await db.officers.find({}, {"_id": 0}).to_list(500)
    
    # 40% of officers have at least one violation
    problem_officers = random.sample(officers, int(len(officers) * 0.4))
    
    for officer in problem_officers:
        # 1-5 violations per problem officer
        num_violations = random.randint(1, 5)
        
        for _ in range(num_violations):
            violation_type = random.choice(VIOLATION_TYPES)
            severity = random.choice(SEVERITIES)
            outcome = random.choice(OUTCOMES)
            
            # Higher severity = more likely sustained
            if severity in [ViolationSeverity.CRITICAL, ViolationSeverity.SERIOUS]:
                outcome = random.choice([ViolationOutcome.SUSTAINED, ViolationOutcome.SUSTAINED, ViolationOutcome.PENDING])
            
            action = DisciplinaryAction.NONE
            settlement = None
            
            if outcome == ViolationOutcome.SUSTAINED:
                if severity == ViolationSeverity.CRITICAL:
                    action = random.choice([DisciplinaryAction.TERMINATION, DisciplinaryAction.SUSPENSION])
                    settlement = random.randint(50000, 500000)
                elif severity == ViolationSeverity.SERIOUS:
                    action = random.choice([DisciplinaryAction.SUSPENSION, DisciplinaryAction.WRITTEN_WARNING])
                    settlement = random.randint(10000, 100000) if random.random() > 0.5 else None
                else:
                    action = random.choice([DisciplinaryAction.VERBAL_WARNING, DisciplinaryAction.WRITTEN_WARNING])
            
            incident_date = (datetime.now() - timedelta(days=random.randint(30, 1095))).strftime("%Y-%m-%d")
            
            await accountability_service.report_violation(
                badge_number=officer["badge_number"],
                department_id=officer["department_id"],
                violation_type=violation_type.value,
                severity=severity.value,
                description=f"Reported {violation_type.value.replace('_', ' ')} incident during traffic stop.",
                incident_date=incident_date,
                reported_by="system_seed",
                ai_confidence=random.uniform(0.75, 0.98) if random.random() > 0.3 else None
            )
            
            # Update outcome if not pending
            if outcome != ViolationOutcome.PENDING:
                violations = await db.officer_violations.find(
                    {"officer_id": officer["officer_id"]},
                    {"_id": 0, "violation_id": 1}
                ).sort("created_at", -1).limit(1).to_list(1)
                
                if violations:
                    await accountability_service.update_violation_outcome(
                        violation_id=violations[0]["violation_id"],
                        outcome=outcome.value,
                        disciplinary_action=action.value,
                        settlement_amount=settlement
                    )
    
    print(f"Violations seeded: {await db.officer_violations.count_documents({})}")


async def seed_database():
    """Run all seed functions"""
    print("=" * 50)
    print("JUSTICE Accountability Database Seeder")
    print("=" * 50)
    
    await seed_departments()
    await seed_officers()
    await seed_violations()
    
    # Recalculate all rankings
    print("\nRecalculating department rankings...")
    await accountability_service.recalculate_all_rankings()
    
    print("\n" + "=" * 50)
    print("Seeding complete!")
    print("=" * 50)
    
    # Print summary
    print(f"\nSummary:")
    print(f"  Departments: {await db.accountability_departments.count_documents({})}")
    print(f"  Officers: {await db.officers.count_documents({})}")
    print(f"  Violations: {await db.officer_violations.count_documents({})}")
    print(f"  Sustained: {await db.officer_violations.count_documents({'outcome': 'sustained'})}")


if __name__ == "__main__":
    asyncio.run(seed_database())
