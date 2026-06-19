// Package mongo wraps go.mongodb.org/mongo-driver into a thin factory.
//
//	client, err := mongo.NewClient(ctx, cfg.MongoURI)
//	defer client.Disconnect(ctx)
package mongo

import (
	"context"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

// NewClient connects, pings, and returns a Mongo client.
func NewClient(ctx context.Context, uri string) (*mongo.Client, error) {
	opts := options.Client().
		ApplyURI(uri).
		SetServerSelectionTimeout(5 * time.Second)

	client, err := mongo.Connect(ctx, opts)
	if err != nil {
		return nil, fmt.Errorf("mongo connect: %w", err)
	}

	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	if err := client.Ping(pingCtx, nil); err != nil {
		_ = client.Disconnect(ctx)
		return nil, fmt.Errorf("mongo ping: %w", err)
	}
	return client, nil
}

// Collection is a convenience getter.
func Collection(client *mongo.Client, db, name string) *mongo.Collection {
	return client.Database(db).Collection(name)
}
