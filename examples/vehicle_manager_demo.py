#!/usr/bin/env python3
"""
Demonstration of Vehicle Manager and Cost Strategy APIs.

This script shows how to use the multi-vehicle and cost strategy features
programmatically. It's useful for understanding the API and for testing.
"""

from datetime import datetime, timedelta
from custom_components.energy_dispatcher.vehicle_manager import VehicleManager
from custom_components.energy_dispatcher.cost_strategy import CostStrategy
from custom_components.energy_dispatcher.models import (
    VehicleConfig,
    ChargerConfig,
    ChargingMode,
    PricePoint,
    CostThresholds,
)


def demo_vehicle_setup():
    """Demonstrate vehicle and charger setup."""
    print("=" * 60)
    print("DEMO 1: Vehicle and Charger Setup")
    print("=" * 60)
    
    # Create a mock Home Assistant instance (simplified for demo)
    class MockHass:
        pass
    
    hass = MockHass()
    manager = VehicleManager(hass)
    
    # Add Tesla Model Y using preset
    tesla = VehicleConfig.tesla_model_y_lr_2022()
    tesla.name = "Family Tesla"
    manager.add_vehicle(tesla)
    print(f"\n✓ Added {tesla.name}")
    print(f"  Battery: {tesla.battery_kwh} kWh")
    print(f"  Max Current: {tesla.max_charge_current}A")
    print(f"  Phases: {tesla.phases}-phase")
    print(f"  Efficiency: {tesla.charging_efficiency * 100}%")
    
    # Add Hyundai Ioniq using preset
    ioniq = VehicleConfig.hyundai_ioniq_electric_2019()
    ioniq.name = "Commuter Ioniq"
    manager.add_vehicle(ioniq)
    print(f"\n✓ Added {ioniq.name}")
    print(f"  Battery: {ioniq.battery_kwh} kWh")
    print(f"  Max Current: {ioniq.max_charge_current}A")
    print(f"  Phases: {ioniq.phases}-phase")
    print(f"  Efficiency: {ioniq.charging_efficiency * 100}%")
    
    # Add charger
    charger = ChargerConfig.generic_3phase_16a()
    charger.name = "Home Wallbox"
    manager.add_charger(charger)
    print(f"\n✓ Added {charger.name}")
    print(f"  Current Range: {charger.min_current}-{charger.max_current}A")
    print(f"  Phases: {charger.phases}-phase")
    
    # Associate Tesla with charger
    manager.associate_vehicle_charger(tesla.id, charger.id)
    print(f"\n✓ Associated {tesla.name} with {charger.name}")
    
    return manager, tesla, ioniq, charger


def demo_charging_calculations(manager, tesla, ioniq):
    """Demonstrate charging calculations."""
    print("\n" + "=" * 60)
    print("DEMO 2: Charging Calculations")
    print("=" * 60)
    
    # Tesla calculations
    print(f"\n{tesla.name}:")
    manager.update_vehicle_state(tesla.id, current_soc=40.0, target_soc=80.0)
    
    required_kwh = manager.calculate_required_energy(tesla.id)
    print(f"  Current SOC: 40%")
    print(f"  Target SOC: 80%")
    print(f"  Energy needed: {required_kwh:.1f} kWh")
    
    hours = manager.calculate_charging_time(tesla.id, 16)
    print(f"  Time at 16A: {hours:.1f} hours ({hours * 60:.0f} minutes)")
    
    # Ioniq calculations
    print(f"\n{ioniq.name}:")
    manager.update_vehicle_state(ioniq.id, current_soc=30.0, target_soc=100.0)
    
    required_kwh = manager.calculate_required_energy(ioniq.id)
    print(f"  Current SOC: 30%")
    print(f"  Target SOC: 100%")
    print(f"  Energy needed: {required_kwh:.1f} kWh")
    
    hours = manager.calculate_charging_time(ioniq.id, 16)
    print(f"  Time at 16A: {hours:.1f} hours ({hours * 60:.0f} minutes)")


def demo_charging_session(manager, tesla, charger):
    """Demonstrate charging session management."""
    print("\n" + "=" * 60)
    print("DEMO 3: Charging Session")
    print("=" * 60)
    
    # Start session with deadline
    deadline = datetime.now() + timedelta(hours=8)
    session = manager.start_charging_session(
        tesla.id,
        charger.id,
        deadline=deadline,
        mode=ChargingMode.DEADLINE
    )
    
    print(f"\n✓ Started charging session")
    print(f"  Vehicle: {tesla.name}")
    print(f"  Start SOC: {session.start_soc}%")
    print(f"  Target SOC: {session.target_soc}%")
    print(f"  Mode: {session.mode.value}")
    print(f"  Deadline: {session.deadline.strftime('%Y-%m-%d %H:%M')}")
    
    # Simulate charging progress
    print(f"\n  Charging in progress...")
    manager.update_vehicle_state(tesla.id, current_soc=65.0)
    print(f"  Current SOC: 65%")
    
    # End session
    manager.update_vehicle_state(tesla.id, current_soc=80.0)
    ended_session = manager.end_charging_session(tesla.id, energy_delivered=30.0)
    
    print(f"\n✓ Session completed")
    print(f"  Final SOC: {ended_session.end_soc}%")
    print(f"  Energy delivered: {ended_session.energy_delivered} kWh")
    duration = (ended_session.end_time - ended_session.start_time).total_seconds() / 3600
    print(f"  Duration: {duration:.1f} hours")


def demo_cost_strategy():
    """Demonstrate cost strategy features."""
    print("\n" + "=" * 60)
    print("DEMO 4: Cost Strategy")
    print("=" * 60)
    
    # Create cost strategy
    thresholds = CostThresholds(cheap_max=1.5, high_min=3.0)
    strategy = CostStrategy(thresholds)
    
    print(f"\nCost Thresholds:")
    print(f"  Cheap: ≤ {thresholds.cheap_max} SEK/kWh")
    print(f"  Medium: {thresholds.cheap_max} - {thresholds.high_min} SEK/kWh")
    print(f"  High: ≥ {thresholds.high_min} SEK/kWh")
    
    # Generate sample prices
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    prices = []
    
    # Pattern: cheap at night, high in morning, medium midday, high evening
    price_pattern = [
        1.0, 1.0, 0.9, 0.8,  # 00-04: Night (cheap)
        1.2, 2.5, 3.5, 4.0,  # 04-08: Morning (high)
        3.0, 2.5, 2.0, 1.5,  # 08-12: Morning->Midday
        1.4, 1.3, 1.5, 1.8,  # 12-16: Midday (medium)
        2.5, 3.0, 3.5, 3.2,  # 16-20: Evening (high)
        2.5, 2.0, 1.5, 1.2,  # 20-24: Evening->Night
    ]
    
    for i, price in enumerate(price_pattern):
        prices.append(PricePoint(
            time=now + timedelta(hours=i),
            spot_sek_per_kwh=price * 0.8,
            enriched_sek_per_kwh=price
        ))
    
    # Cost classification
    print(f"\nCost Classification (next 24 hours):")
    summary = strategy.get_cost_summary(prices, now, 24)
    print(f"  Total hours: {summary['total_hours']}")
    print(f"  Cheap hours: {summary['cheap_hours']}")
    print(f"  Medium hours: {summary['medium_hours']}")
    print(f"  High hours: {summary['high_hours']}")
    print(f"  Avg price: {summary['avg_price']:.2f} SEK/kWh")
    print(f"  Min price: {summary['min_price']:.2f} SEK/kWh")
    print(f"  Max price: {summary['max_price']:.2f} SEK/kWh")
    
    # High-cost windows
    windows = strategy.predict_high_cost_windows(prices, now, 24)
    print(f"\nHigh-Cost Windows:")
    for i, (start, end) in enumerate(windows, 1):
        duration = (end - start).total_seconds() / 3600
        print(f"  {i}. {start.strftime('%H:%M')} - {end.strftime('%H:%M')} ({duration:.0f}h)")
    
    # Battery reserve
    reserve = strategy.calculate_battery_reserve(
        prices, now, battery_capacity_kwh=15.0, current_soc=50.0
    )
    print(f"\nBattery Reserve Recommendation:")
    print(f"  Current SOC: 50%")
    print(f"  Recommended reserve: {reserve:.0f}%")
    print(f"  Reason: Preserve capacity for high-cost windows")
    
    # EV charging optimization
    print(f"\nEV Charging Optimization:")
    required_kwh = 30.0
    charging_hours = strategy.optimize_ev_charging_windows(
        prices, now, required_kwh, charging_power_kw=11.0
    )
    print(f"  Energy needed: {required_kwh} kWh")
    print(f"  Charging power: 11 kW")
    print(f"  Optimal hours: {len(charging_hours)}")
    print(f"  Selected times:")
    for hour in charging_hours[:5]:  # Show first 5
        price = next(p for p in prices if p.time == hour)
        print(f"    {hour.strftime('%H:%M')} - {price.enriched_sek_per_kwh:.2f} SEK/kWh")


def demo_charging_modes():
    """Demonstrate different charging modes."""
    print("\n" + "=" * 60)
    print("DEMO 5: Charging Modes")
    print("=" * 60)
    
    modes = [
        (ChargingMode.ASAP, "Charge immediately, ignore cost"),
        (ChargingMode.ECO, "Optimize for solar and cheap hours"),
        (ChargingMode.DEADLINE, "Meet specific time requirement"),
        (ChargingMode.COST_SAVER, "Minimize cost, flexible timing"),
    ]
    
    print("\nAvailable Charging Modes:")
    for mode, description in modes:
        print(f"\n  {mode.value.upper()}")
        print(f"    {description}")
        
        if mode == ChargingMode.ASAP:
            print(f"    Use case: Emergency, urgent travel, low SOC")
        elif mode == ChargingMode.ECO:
            print(f"    Use case: Flexible timing, good solar forecast")
        elif mode == ChargingMode.DEADLINE:
            print(f"    Use case: Morning commute, planned trip")
        elif mode == ChargingMode.COST_SAVER:
            print(f"    Use case: Cost priority, ample time available")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("Energy Dispatcher - Vehicle Manager & Cost Strategy Demo")
    print("=" * 60)
    
    # Demo 1: Setup
    manager, tesla, ioniq, charger = demo_vehicle_setup()
    
    # Demo 2: Calculations
    demo_charging_calculations(manager, tesla, ioniq)
    
    # Demo 3: Session
    demo_charging_session(manager, tesla, charger)
    
    # Demo 4: Cost Strategy
    demo_cost_strategy()
    
    # Demo 5: Modes
    demo_charging_modes()
    
    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("\nFor more information, see:")
    print("  - docs/multi_vehicle_setup.md")
    print("  - examples/multi_vehicle_config.yaml")
    print()


if __name__ == "__main__":
    main()
