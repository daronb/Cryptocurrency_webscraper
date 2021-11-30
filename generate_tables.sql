-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';



-- -----------------------------------------------------
-- Schema reddit_data
-- -----------------------------------------------------

-- -----------------------------------------------------
-- Schema reddit_data
-- -----------------------------------------------------

CREATE SCHEMA IF NOT EXISTS `reddit_data` DEFAULT CHARACTER SET utf8 ;
USE `reddit_data` ;

-- -----------------------------------------------------
-- Table `reddit_data`.`user`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `reddit_data`.`user` (
  `user_id` INT NOT NULL AUTO_INCREMENT,
  `user_name` VARCHAR(45) NOT NULL,
  `post_karma` INT NOT NULL,
  `comment_karma` INT NOT NULL,
  `date_joined` DATETIME NOT NULL,
  PRIMARY KEY (`user_id`))
ENGINE = InnoDB;

-- create a unique index on the user table to avoid duplicates
CREATE UNIQUE INDEX idx_user
ON user(user_name, date_joined);

-- -----------------------------------------------------
-- Table `reddit_data`.`post`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `reddit_data`.`post` (
  `post_id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `title` TEXT NOT NULL,
  `likes` INT NOT NULL,
  `comments` INT NOT NULL,
  `date_posted` DATETIME NOT NULL,
  `sub_reddit` VARCHAR(45) NOT NULL,
  `post_source` ENUM('user', 'subreddit') NOT NULL,
  `post_option` ENUM('top', 'new') NOT NULL,
  PRIMARY KEY (`post_id`),
  INDEX `user_id_idx` (`user_id` ASC) VISIBLE,
  CONSTRAINT `user_id`
    FOREIGN KEY (`user_id`)
    REFERENCES `reddit_data`.`user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;

-- alter to allow for emojis
ALTER TABLE post CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

-- unique index for post
CREATE UNIQUE INDEX idx_post
ON post(user_id, date_posted, sub_reddit, post_source);

-- -----------------------------------------------------
-- Table `reddit_data`.`comment`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `reddit_data`.`comment` (
  `comments_id` INT NOT NULL AUTO_INCREMENT,
  `post_id` INT NOT NULL,
  `author` VARCHAR(45) NOT NULL,
  `text` TEXT NOT NULL,
  `comment_date` DATETIME NOT NULL,
  `sub_comments` INT NOT NULL,
  `parent_comment_id` int NULL,
  `reddit_parent_id` varchar(20) NULL,
  `reddit_comment_id` varchar(20) NULL, 
  `reddit_post_id`  varchar(20) NULL, 
  PRIMARY KEY (`comments_id`),
  INDEX `p_idx` (`post_id` ASC) VISIBLE,
  INDEX `parent_comment_id_idx` (`parent_comment_id` ASC) VISIBLE,
  CONSTRAINT `post_id`
    FOREIGN KEY (`post_id`)
    REFERENCES `reddit_data`.`post` (`post_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `parent_comment_id`
    FOREIGN KEY (`parent_comment_id`)
    REFERENCES `reddit_data`.`comment` (`comments_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;

-- alter to allow for emojis
ALTER TABLE comment CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

-- unique index for comment
CREATE UNIQUE INDEX idx_comment 
ON comment(post_id, reddit_comment_id, comment_date);

SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
