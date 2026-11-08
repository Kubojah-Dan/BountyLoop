export type FoodCategory =
  | 'produce_fruit'
  | 'produce_vegetable'
  | 'bread_bakery'
  | 'dairy'
  | 'grains_staples'
  | 'prepared_cooked'
  | 'meat_fish'
  | 'soup_stew'
  | 'dessert_bakery_sweet'
  | 'beverage'
  | 'condiment_sauce'
  | 'other_unclassified';

export type FreshnessGrade =
  | 'grade_0_spoiled'
  | 'grade_1_poor'
  | 'grade_2_good'
  | 'grade_3_fresh';

export type HazardFlag =
  | 'none'
  | 'suspected_contamination_or_formalin';

export type DonationStatus =
  | 'draft'
  | 'open'
  | 'matched'
  | 'picked_up'
  | 'cancelled'
  | 'spoiled';

export type ReviewStatus = 'pending' | 'resolved' | 'escalated';

export interface Donation {
  id: string;
  donor_id: string;
  donor_name?: string | null;
  donor_address?: string | null;
  item: FoodCategory;
  item_confidence: number;
  freshness: FreshnessGrade;
  freshness_confidence: number;
  hazard_flag: HazardFlag;
  est_weight_kg: number;
  expires_at: string;
  status: DonationStatus;
  needs_review: boolean;
  photo_paths: string[];
  created_at: string;
  model_versions?: Record<string, string>;
}

export interface ReviewQueueItem {
  id: string;
  donation_id: string;
  status: ReviewStatus;
  review_reason: string;
  created_at: string;
  resolved_at?: string | null;
  donation?: Donation;
}

export interface ImpactSummary {
  kg_rescued: number;
  meals_equivalent: number;
  co2e_avoided_kg: number;
  donations_count: number;
  claims_completed: number;
  median_time_to_pickup_min: number;
  auto_match_rate: number;
  model_accuracy_proxy: number;
}

export interface Recipient {
  id: string;
  org_name: string;
  address: string;
  latitude: number;
  longitude: number;
  capacity_kg_per_day: number;
  is_accepting: boolean;
  accepted_items: FoodCategory[];
  phone_e164?: string;
  operating_hours?: Record<string, string>;
}

