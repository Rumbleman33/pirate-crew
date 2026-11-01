CREATE TABLE `registered_captains` (
	`username` text PRIMARY KEY NOT NULL,
	`display_name` text NOT NULL,
	`player_id` integer NOT NULL,
	`salt` text NOT NULL,
	`password_hash` text NOT NULL,
	`created` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `registered_captains_player_id_unique` ON `registered_captains` (`player_id`);